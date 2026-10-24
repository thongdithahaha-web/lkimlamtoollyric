import sys
import json
import re
from dataclasses import dataclass
import torch
import glob
import os
import shutil

# UTF-8 encoding for Windows stdout/stderr
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Safe import for vinorm / fallback for Windows & Python >= 3.12
_NUM_WORDS = {
    '0': 'không', '1': 'một', '2': 'hai', '3': 'ba', '4': 'bốn',
    '5': 'năm', '6': 'sáu', '7': 'bảy', '8': 'tám', '9': 'chín'
}

try:
    from vinorm import TTSnorm
except Exception:
    def TTSnorm(text, *args, **kwargs):
        words = []
        for c in text:
            if c in _NUM_WORDS:
                words.append(_NUM_WORDS[c])
            else:
                words.append(c)
        return " ".join(" ".join(words).split())

from regtag import augment, reoov, clean_text

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
READ_MAP_FILE = os.path.join(CURRENT_DIR, 'read_map.json')
if os.path.exists(READ_MAP_FILE):
    with open(READ_MAP_FILE, 'r', encoding='utf-8') as file:
        exeption_oov = json.load(file)
else:
    exeption_oov = {}

@dataclass
class Point:
    token_index: int
    time_index: int
    score: float
    
# Merge the labels
@dataclass
class Segment:
    label: str
    start: int
    end: int
    score: float

    def __repr__(self):
        return f"{self.label}\t({self.score:4.2f}): [{self.start:5d}, {self.end:5d})"

    @property
    def length(self):
        return self.end - self.start
    

def itn_text(word):
    if not word or not word.strip():
        return ""
    word = word.lower().strip(' -.?!,)("\'…“”*_[]’')
    word = re.sub(r'[ {}]'.format(re.escape('-.?!,)("\'…“”*_[]’')), ' ', word)
    word = re.sub(r'\s+', ' ', word)
    if reoov.check_oov_word(word) or reoov.format_word(word) not in reoov.vi_dict or augment.get_random_oov(word) is not None or exeption_oov.get(word, None) is not None:
        if exeption_oov.get(word, None) is not None:
            return exeption_oov[word]
        read_form = augment.get_random_oov(word)
        if read_form is not None:
            tgt = augment.oov_dict[word]
            tgt.sort()
            tgt = tgt[0]
            return tgt
        if len(set(list(word)).intersection(set(list('0123456789')))) > 0:
            read_form = TTSnorm(word).lower().strip('. ')
            return read_form
    return word     

def norm_word(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip(' -.?!,)("\'…“”*_[]’')
    words = text.lower().strip('., :?').split()
    norm = [itn_text(w) for w in words]
    return ' '.join(norm)


def get_trellis(emission, tokens, blank_id=0):
    num_frame = emission.size(0)
    num_tokens = len(tokens)

    trellis = torch.empty((num_frame + 1, num_tokens + 1))
    trellis[0, 0] = 0
    trellis[1:, 0] = torch.cumsum(emission[:, 0], 0)
    if num_tokens > 0:
        trellis[0, 1:] = -float("inf")
        if num_tokens < num_frame + 1:
            trellis[-num_tokens:, 0] = float("inf")

    for t in range(num_frame):
        trellis[t + 1, 1:] = torch.maximum(
            trellis[t, 1:] + emission[t, blank_id],
            trellis[t, :-1] + emission[t, tokens],
        )
    return trellis

def backtrack(trellis, emission, tokens, blank_id=0):
    j = trellis.size(1) - 1
    t_start = torch.argmax(trellis[:, j]).item()

    path = []
    for t in range(t_start, 0, -1):
        stayed = trellis[t - 1, j] + emission[t - 1, blank_id]
        changed = trellis[t - 1, j - 1] + emission[t - 1, tokens[j - 1]]

        prob = emission[t - 1, tokens[j - 1] if changed > stayed else 0].exp().item()
        path.append(Point(j - 1, t - 1, prob))

        if changed > stayed:
            j -= 1
            if j == 0:
                break
    else:
        raise ValueError("Failed to align")
    return path[::-1]

def merge_repeats(path, transcript):
    i1, i2 = 0, 0
    segments = []
    while i1 < len(path):
        while i2 < len(path) and path[i1].token_index == path[i2].token_index:
            i2 += 1
        score = sum(path[k].score for k in range(i1, i2)) / max(1, (i2 - i1))
        segments.append(
            Segment(
                transcript[path[i1].token_index],
                path[i1].time_index,
                path[i2 - 1].time_index + 1,
                score,
            )
        )
        i1 = i2
    return segments


# Merge words
def merge_words(segments, separator="|"):
    words = []
    i1, i2 = 0, 0
    while i1 < len(segments):
        if i2 >= len(segments) or segments[i2].label == separator:
            if i1 != i2:
                segs = segments[i1:i2]
                word = "".join([seg.label for seg in segs])
                total_len = sum(seg.length for seg in segs)
                score = sum(seg.score * seg.length for seg in segs) / max(1, total_len)
                words.append(Segment(word, segments[i1].start, segments[i2 - 1].end, score))
            i1 = i2 + 1
            i2 = i1
        else:
            i2 += 1
    return words


def add_pad(word_segments, emission, shift_val=1):
    for i in range(len(word_segments) - 1):
        word = word_segments[i]
        next_word = word_segments[i + 1]
        next_word.start -= shift_val
        if next_word.start - word.start > 150:
            word.end = word.start + 150
        else:
            word.end = next_word.start
        next_word.start -= shift_val
        
    if len(word_segments) > 0:
        word_segments[-1].end = min(len(emission), word_segments[-1].end + 200)
        word_segments[0].start = max(0, word_segments[0].start - 50)
    
    return word_segments

def shift_align(lyric_alignment, shift_ms=120):
    words = [item for sublist in [seg['l'] for seg in lyric_alignment] for item in sublist]
    for i in range(len(words)):
        shif_val_s = 0 if (words[i]['s'] - shift_ms) < 0 else shift_ms
        shif_val_e = 0 if (words[i]['e'] - shift_ms) < words[i]['s'] else shift_ms
        words[i]['s'] -= shif_val_s
        words[i]['e'] -= shif_val_e
    for seg in lyric_alignment:
        if len(seg['l']) > 0:
            seg['s'] = seg['l'][0]['s']
            seg['e'] = seg['l'][-1]['e']
    
    return lyric_alignment

def load_test_case(data_path):
    all_wav_file = glob.glob(os.path.join(data_path, '**/*_normed_16k.wav'), recursive=True)
    all_json_file = glob.glob(os.path.join(data_path, '**/*.json'), recursive=True)
    map_test_case = dict({})
    for item in all_wav_file:
        item_id = os.path.basename(item).split('_')[0]
        if map_test_case.get(item_id, None) is None:
            map_test_case[item_id] = {
                'path_wav': item
            }
            
    for item in all_json_file:
        item_id = os.path.basename(item).split('.')[0]
        if map_test_case.get(item_id, None) is not None:
            map_test_case[item_id]['path_lyric'] = item
    return map_test_case

def zip_folder(input_folder_path, output_zip_path):
    shutil.make_archive(output_zip_path, 'zip', input_folder_path)

if __name__ == "__main__":
    print("Testing norm_word:", norm_word("Xin chào 2026!"))
