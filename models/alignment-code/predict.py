import os
import sys
import json
import time
import csv
import torch
import torchaudio
from tqdm import tqdm
from transformers import AutoTokenizer, AutoFeatureExtractor
from model_handling import Wav2Vec2ForCTC
import utils

# UTF-8 stdout/stderr encoding for Windows console
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

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
use_gpu = torch.cuda.is_available()

model_path = 'nguyenvulebinh/lyric-alignment'
model = None
tokenizer = None
feature_extractor = None
vocab = None

def load_model():
    global model
    global tokenizer
    global feature_extractor
    global vocab

    has_local_weights = os.path.isdir(model_path) and any(
        os.path.exists(os.path.join(model_path, fname)) and os.path.getsize(os.path.join(model_path, fname)) > 1024 * 1024
        for fname in ["pytorch_model.bin", "model.safetensors"]
    )
    if has_local_weights:
        target_path = model_path
        print(f"[INFO] Loading model from local path: {target_path}")
    else:
        target_path = "nguyenvulebinh/lyric-alignment"
        print(f"[INFO] Local weights not found in '{model_path}'. Downloading/loading from HuggingFace Hub: {target_path}")

    model = Wav2Vec2ForCTC.from_pretrained(target_path).eval()
    tokenizer = AutoTokenizer.from_pretrained(target_path)
    feature_extractor = AutoFeatureExtractor.from_pretrained(target_path)
    
    if use_gpu:
        model = model.to(device)
        print(f"[INFO] Model moved to GPU ({device}).")
    else:
        print("[INFO] Model running on CPU.")
        
    vocab = [tokenizer.convert_ids_to_tokens(i) for i in range(len(tokenizer.get_vocab()))]


def do_asr(waveform):
    input_values = feature_extractor.pad([
        {"input_values": feature_extractor(item, sampling_rate=16000)["input_values"][0]} for item in
        waveform
    ], return_tensors='pt')["input_values"]
    
    if use_gpu:
        input_values = input_values.to(device)

    out_values = model(input_values=input_values)
    logits = out_values.logits[0]

    emissions = torch.log_softmax(logits, dim=-1)
    emission = emissions.cpu().detach()
    emission[emission < -20] = -20

    emission[:, tokenizer.convert_tokens_to_ids('|')] = torch.tensor([
        max(item) for item in list(zip(emission[:, tokenizer.convert_tokens_to_ids('|')], emission[:, tokenizer.convert_tokens_to_ids('<pad>')]))
    ])
    emission[:, tokenizer.convert_tokens_to_ids('<pad>')] = -20
    
    return emission

def do_force_align(waveform, emission, word_list, sample_rate=16000, base_stamp=0):
    clean_words = [w.replace('|', '').strip() for w in word_list if w.replace('|', '').strip()]
    if not clean_words:
        return []
    transcript = '|'.join(clean_words)
    dictionary = {c: i for i, c in enumerate(vocab)}
    tokens = [dictionary.get(c, 0) for c in transcript]
    trellis = utils.get_trellis(emission, tokens, blank_id=tokenizer.convert_tokens_to_ids('|'))
    path = utils.backtrack(trellis, emission, tokens)
    segments = utils.merge_repeats(path, transcript)
    word_segments = utils.merge_words(segments)
    word_segments = utils.add_pad(word_segments, emission)
    ratio = waveform.size(1) / max(1, trellis.size(0) - 1)
    result = []
    for word in word_segments:
        x0 = int(ratio * word.start)
        x1 = int(ratio * word.end)
        result.append({
            'd': word.label,
            's': int(x0 / sample_rate * 1000) + base_stamp,
            'e': int(x1 / sample_rate * 1000) + base_stamp
        })
    return result

def fallback_linear_align(waveform, lyric_alignment_json, sample_rate=16000):
    total_ms = int(waveform.size(1) / sample_rate * 1000)
    num_segs = len(lyric_alignment_json)
    if num_segs == 0:
        return lyric_alignment_json
        
    seg_duration = max(1000, total_ms // num_segs)
    for s_idx, seg in enumerate(lyric_alignment_json):
        s_time = s_idx * seg_duration
        e_time = min(total_ms, (s_idx + 1) * seg_duration)
        seg['s'] = s_time
        seg['e'] = e_time
        words = seg.get('l', [])
        if words:
            word_dur = max(100, (e_time - s_time) // len(words))
            for w_idx, w in enumerate(words):
                w['s'] = s_time + w_idx * word_dur
                w['e'] = min(e_time, s_time + (w_idx + 1) * word_dur)
    return lyric_alignment_json

def handle_sample(wav, lyric_alignment_json):        
    seg_words = [[word['d'] for word in seg.get('l', [])] for seg in lyric_alignment_json]
    words = [y for x in seg_words for y in x]
    
    if not words:
        return lyric_alignment_json
        
    words_norm = [utils.norm_word(word) for word in words]
    single_words_list = [word.split() if word.split() else [word] for word, word_raw in zip(words_norm, words)]
    single_words = [y for x in single_words_list for y in x]
    
    if not single_words:
        return fallback_linear_align(wav, lyric_alignment_json)
        
    # wav to text_prob
    emission = do_asr(wav)
    
    try:
        word_piece = do_force_align(wav, emission, single_words)
        if len(word_piece) != len(single_words):
            print(f"[WARN] Force align returned {len(word_piece)} pieces, expected {len(single_words)}. Falling back to linear align.")
            return fallback_linear_align(wav, lyric_alignment_json)
    except Exception as e:
        print(f"[WARN] Force alignment exception ({e}), applying linear timing fallback.")
        return fallback_linear_align(wav, lyric_alignment_json)
    
    # single_words -> words_norm
    words_align_result = []
    word_piece_idx = 0
    for idx in range(len(words)):
        len_single_words = len(single_words_list[idx])
        list_piece_align = word_piece[word_piece_idx: word_piece_idx + len_single_words]
        word_piece_idx += len_single_words
        words_align_result.append(list_piece_align)
        
    # words_norm -> seg_words
    seg_words_align_result = []
    word_idx = 0
    for idx in range(len(seg_words)):
        len_seg = len(seg_words[idx])
        list_word_align = words_align_result[word_idx: word_idx + len_seg]
        word_idx += len_seg
        seg_words_align_result.append(list_word_align)
    
    # Fill result align
    for list_word_align, segment_info in zip(seg_words_align_result, lyric_alignment_json):
        for idx, (word_align, word_raw) in enumerate(zip(list_word_align, segment_info.get('l', []))):
            if len(word_align) > 0:
                word_raw['s'] = word_align[0]['s']
                word_raw['e'] = word_align[-1]['e']
            elif idx > 0:
                prev_e = segment_info['l'][idx-1].get('e', 0)
                word_raw['s'] = prev_e
                word_raw['e'] = prev_e + 100
            else:
                word_raw['s'] = 0
                word_raw['e'] = 100
        if len(segment_info.get('l', [])) > 0:
            segment_info['s'] = segment_info['l'][0]['s']
            segment_info['e'] = segment_info['l'][-1]['e']
        
    return lyric_alignment_json
    

def main(data_path, output_path):
    if not os.path.exists(os.path.join(output_path, 'json')):
        os.makedirs(os.path.join(output_path, 'json'))
    load_model()
    all_test_case = utils.load_test_case(data_path)
    all_predicted_time = []
    total_audio_time = 0
    total_predicted_time = 0
    for sid in tqdm(all_test_case.keys()):
        t1 = time.time()
        wav, rate = torchaudio.load(all_test_case[sid]['path_wav'])
        total_audio_time += wav.size(-1) / rate * 1000
        with open(all_test_case[sid]['path_lyric'], 'r', encoding='utf-8') as file:
            raw_lyric_alignment = json.load(file)
        try:
            lyric_alignment_json = handle_sample(wav, raw_lyric_alignment)
            with open(os.path.join(output_path, 'json', "{}.json".format(sid)), 'w', encoding='utf-8') as file:
                json.dump(lyric_alignment_json, file, indent=4, ensure_ascii=False)
        except Exception:
            print("File error ", sid)
            with open(os.path.join(output_path, 'json', "{}.json".format(sid)), 'w', encoding='utf-8') as file:
                json.dump(raw_lyric_alignment, file, indent=4, ensure_ascii=False)
        t2 = time.time()
        
        predicted_time = int(t2 * 1000 - t1 * 1000)
        total_predicted_time += predicted_time
        all_predicted_time.append((sid + ".json", predicted_time))
    
    # Make submission.zip file
    utils.zip_folder(os.path.join(output_path, 'json'), os.path.join(output_path, 'submission'))
    # time_submission.csv
    with open(os.path.join(output_path, 'time_submission.csv'), 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(('fname', 'time'))
        for item in all_predicted_time:
            writer.writerow(item)
            
    if total_predicted_time > 0:
        print("Audio time / Process time = {:.2f}".format(total_audio_time / total_predicted_time))
    
if __name__ == "__main__":
    if len(sys.argv) > 2:
        main(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python predict.py <input_folder> <output_folder>")
