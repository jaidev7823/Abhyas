import os
import torch
import ollama
import librosa
import numpy as np
from datetime import datetime
from faster_whisper import WhisperModel
from speechbrain.inference.interfaces import foreign_class

# --- CONFIGURATION ---
VIDEO_FILE = "video.mp4"
AUDIO_FILE = "temp_audio.wav"
MODELS_DIR = "./models"
WHISPER_PATH = os.path.join(MODELS_DIR, "faster-whisper-large-v3")
OLLAMA_MODEL = "gemma4:latest"

# Create a unique folder for this review session
SESSION_DIR = f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(SESSION_DIR, exist_ok=True)

TRANSCRIPT_FILE = os.path.join(SESSION_DIR, "transcript.txt")
ANALYSIS_FILE = os.path.join(SESSION_DIR, "vinh_giang_report.txt")

def extract_audio(input_file, output_file):
    if os.path.exists(output_file): return
    print("-> Extracting audio from video...")
    os.system(f"ffmpeg -i {input_file} -ar 16000 -ac 1 -c:a pcm_s16le {output_file} -y -loglevel quiet")

def transcribe_audio(audio_path):
    if os.path.exists(TRANSCRIPT_FILE):
        with open(TRANSCRIPT_FILE, "r") as f: return f.read()

    print(f"-> Transcribing with Whisper (Large-V3) on GPU...")
    model = WhisperModel(WHISPER_PATH, device="cuda", compute_type="float16")
    segments, _ = model.transcribe(audio_path, beam_size=5)
    full_text = " ".join([segment.text for segment in segments])
    
    with open(TRANSCRIPT_FILE, "w") as f:
        f.write(full_text)
    return full_text

def get_voice_metrics(audio_path):
    print("-> Analyzing vocal dynamics (Librosa)...")
    y, sr = librosa.load(audio_path)
    
    # 1. Pitch (Stability vs Variation)
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = pitches[pitches > 0]
    pitch_std = np.std(pitch_values) if len(pitch_values) > 0 else 0
    
    # 2. Energy/Volume (RMS)
    rms = librosa.feature.rms(y=y)[0]
    avg_volume = np.mean(rms)
    vol_std = np.std(rms)
    
    # 3. Tempo (WPM/BPM)
    # tempo is returned as an array, so we take the first element [0]
    tempo_array, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(tempo_array[0]) if isinstance(tempo_array, (np.ndarray, list)) else float(tempo_array)
    
    return {
        "pitch_variation": "High (Expressive)" if pitch_std > 500 else "Low (Monotone)",
        "volume_stability": "Dynamic" if vol_std > 0.02 else "Flat/Whispery",
        "average_volume": round(float(avg_volume), 4),
        "tempo_wpm": round(tempo, 1)
    }

WAV2VEC_PATH = "./models/emotion-recognition"

def analyze_tone_emotion(audio_path):
    print("-> Detecting emotion (SpeechBrain)...")
    classifier = foreign_class(
        source=WAV2VEC_PATH,
        pymodule_file="custom_interface.py",
        classname="CustomEncoderWav2vec2Classifier",
        # Changed "cuda" to "cuda:0" to fix the 'unpack' error
        run_opts={"device":"cuda:0"}, 
        savedir=WAV2VEC_PATH 
    )
    # The classify_file method for THIS model returns 4 values
    out_prob, score, index, text_lab = classifier.classify_file(audio_path)
    return text_lab[0]

def get_vinh_giang_review(transcript, emotion, metrics):
    print(f"-> Sending data to {OLLAMA_MODEL}...")
    
    prompt = f"""
    You are a Communication Expert (style: Vinh Giang). Analyze this performance:
    
    TRANSCRIPT: "{transcript}"
    EMOTIONAL TONE: {emotion}
    VOCAL METRICS:
    - Pitch Variation: {metrics['pitch_variation']}
    - Volume Dynamics: {metrics['volume_stability']} (Avg: {metrics['average_volume']})
    - Speaking Rate: {metrics['tempo_wpm']} BPM
    
    PROVIDE A DETECTIVE-LEVEL ANALYSIS:
    1. PRO-PRONUNCIATION: Identify 3 words from the transcript where the speaker likely struggled with clarity (specifically check 'th', 's', and 'r' sounds).
    2. THE "VOLUME GAP": If volume is low or stability is "Flat", explain how to use 'Vocal Projection'.
    3. FILLER AUDIT: Count "like", "um", "actually" and explain how they hurt the 'Authority' of the speech.
    4. ACTIONABLE TIP: Give one specific exercise to fix the detected "{emotion}" monotone.
    5. RANK: Professionalism Score (1-10).
    """
    
    response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
    return response['message']['content']

def main():
    try:
        extract_audio(VIDEO_FILE, AUDIO_FILE)
        
        # Data Gathering
        text = transcribe_audio(AUDIO_FILE)
        emotion = analyze_tone_emotion(AUDIO_FILE)
        metrics = get_voice_metrics(AUDIO_FILE)
        
        # Expert Coaching
        report = get_vinh_giang_review(text, emotion, metrics)
        
        # Save results to the folder
        with open(ANALYSIS_FILE, "w") as f:
            f.write(f"--- SESSION METRICS ---\nEmotion: {emotion}\nMetrics: {metrics}\n\n")
            f.write(f"--- COACHING REPORT ---\n{report}")
            
        print(f"\nReview Complete! Folder: {SESSION_DIR}")
        
    finally:
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

if __name__ == "__main__":
    main()
