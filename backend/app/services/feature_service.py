import librosa
import numpy as np
from scipy.signal import medfilt

from app.core.config import TARGET_SR
STEP = 3

def extract_pause_regions(pause_mask, times):
    regions = []
    i = 0
    while i < len(pause_mask):
        if pause_mask[i]:
            start = times[i]
            while i < len(pause_mask) and pause_mask[i]:
                i += 1
            end = times[i - 1] if i > 0 else times[-1]
            if end - start >= 0.05:
                regions.append({"start": float(start), "end": float(end)})
        else:
            i += 1
    return regions
def smooth_signal(signal, window_size=15):

    kernel = np.ones(window_size) / window_size

    return np.convolve(
        signal,
        kernel,
        mode="same"
    )


def extract_features(audio_path):
    y, sr = librosa.load(audio_path, sr=TARGET_SR)

    hop_length = 256
    rms = librosa.feature.rms(
        y=y,
        hop_length=hop_length
    )[0]
        
    rms = smooth_signal(rms, window_size=25)

    pitch = librosa.yin(y, fmin=50, fmax=300, sr=sr, hop_length=hop_length)
    pitch = np.nan_to_num(pitch, nan=0.0)
    pitch = medfilt(pitch, kernel_size=21)
    
    pitch = smooth_signal(
        pitch,
        window_size=15
    )

    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    pause_mask = rms < np.percentile(rms, 15)

    delta_rms = np.abs(np.diff(rms, prepend=rms[0]))
    cps = np.convolve(
        delta_rms,
        np.ones(20) / 20,
        mode="same"
    )
    
    cps = smooth_signal(
        cps,
        window_size=20
    )

    pause_regions = extract_pause_regions(pause_mask, times)
    times = times[::STEP]
    rms = rms[::STEP]
    pitch = pitch[::STEP]
    cps = cps[::STEP]
    pause_mask = pause_mask[::STEP]

    return {
        "rms": rms.tolist(),
        "pitch": pitch.tolist(),
        "times": times.tolist(),
        "pause_mask": pause_mask.tolist(),
        "pause_regions": pause_regions,
        "cps": cps.tolist(),
        "duration": float(len(y) / sr),
        "sample_rate": sr,
    }
