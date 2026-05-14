# Pro-Speech Analyzer

An AI-powered pipeline to analyze speech for clarity, tone, and "executive presence." It uses Whisper for transcription, SpeechBrain for emotion detection, and Librosa for vocal dynamics.

## Project Structure
Ensure your models folder is structured exactly as follows:
```text

├── main.py
├── video.mp4
└── models/
    ├── faster-whisper-large-v3/
    └── emotion-recognition/
        ├── custom_interface.py
        ├── hyperparams.yaml
        ├── model.ckpt
        └── label_encoder.txt
```

## Cross-Platform Setup Guide

### Linux (CachyOS / Arch / Ubuntu)
* Drivers: Ensure nvidia-utils and cuda are installed.
* Environment: Use export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib if libraries aren't found.
* Performance: Best performance for faster-whisper using CUDA.

### Windows
1. CUDA: Install the NVIDIA CUDA Toolkit (12.x).
2. FFmpeg: Download the FFmpeg essentials build, extract it, and add the bin folder to your System PATH.
3. Python Path: In main.py, the script uses os.path.join so it is Windows-ready.
4. C++ Redistributable: Ensure you have the Visual C++ Redistributable installed for CTranslate2.

### macOS (M1/M2/M3 Apple Silicon)
1. Drivers: macOS uses Metal (MPS) instead of CUDA.
2. Main.py Update: You must change device="cuda" to device="cpu" (or device="mps") in the WhisperModel and foreign_class calls.
3. Dependencies:
   brew install ffmpeg libsndfile
   pip install torch torchvision torchaudio

---

## Common Troubleshooting
* Error: libcublas.so missing: (Linux) Re-link your libraries or install nvidia-cublas-cu12.
* Error: ffmpeg not found: Ensure the command ffmpeg -version works in your terminal before running.
* Error: OutOfMemory: If your GPU VRAM is low, change compute_type="float16" to compute_type="int8_float16".
