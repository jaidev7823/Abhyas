import os
import torch
import ollama
from faster_whisper import WhisperModel
from speechbrain.inference.interfaces import foreign_class

# --- CONFIGURATION ---
VIDEO_FILE = "video.mp4"
AUDIO_FILE = "temp_audio.wav"
TRANSCRIPT_FILE = "transcript.txt"
ANALYSIS_FILE = "review_report.txt"
MODEL_PATH = "./models/faster-whisper-large-v3"
OLLAMA_MODEL = "gemma4:latest"

def extract_audio(input_file, output_file):
    if os.path.exists(output_file): return
    print("-> Extracting audio...")
    os.system(f"ffmpeg -i {input_file} -ar 16000 -ac 1 -c:a pcm_s16le {output_file} -y -loglevel quiet")

def transcribe_audio(audio_path):
    # Check if transcript already exists to save time
    if os.path.exists(TRANSCRIPT_FILE):
        print(f"-> Found existing {TRANSCRIPT_FILE}, skipping transcription.")
        with open(TRANSCRIPT_FILE, "r") as f:
            return f.read()

    print(f"-> Transcribing with Whisper (Large-V3) on GPU...")
    model = WhisperModel(MODEL_PATH, device="cuda", compute_type="float16")
    segments, _ = model.transcribe(audio_path, beam_size=5)
    full_text = " ".join([segment.text for segment in segments])
    
    with open(TRANSCRIPT_FILE, "w") as f:
        f.write(full_text)
    return full_text

def analyze_tone(audio_path):
    print("-> Analyzing tone and emotion with SpeechBrain on GPU...")
    # Loading the classifier and moving to GPU
    classifier = foreign_class(
        source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
        pymodule_file="custom_interface.py",
        classname="CustomEncoderWav2vec2Classifier",
        run_opts={"device":"cuda"} # This ensures SpeechBrain uses the GPU
    )
    out_prob, score, index, text_lab = classifier.classify_file(audio_path)
    return text_lab[0]

def get_ollama_review(transcript, tone):
    print("-> Getting feedback from Ollama...")
    prompt = f"""
    Analyze the following English transcript and vocal tone:
    
    TONE DETECTED: {tone}
    TRANSCRIPT: "{transcript}"
    
    Provide:
    1. Grammatical and vocabulary fixes.
    2. A proficiency rank (1-10).
    3. Suggestions for tone/accent improvement.
    """
    
    response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
    return response['message']['content']

def main():
    try:
        extract_audio(VIDEO_FILE, AUDIO_FILE)
        
        # This will now skip if transcript.txt exists
        text = transcribe_audio(AUDIO_FILE)
        
        tone = analyze_tone(AUDIO_FILE)
        report = get_ollama_review(text, tone)
        
        with open(ANALYSIS_FILE, "w") as f:
            f.write(f"--- TRANSCRIPT ---\n{text}\n\n--- TONE ---\n{tone}\n\n--- ANALYSIS ---\n{report}")
            
        print(f"\nDone! Check {ANALYSIS_FILE}")
        
    finally:
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

if __name__ == "__main__":
    main()
