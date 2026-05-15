import librosa
import numpy as np

from scipy.signal import medfilt

from app.core.config import TARGET_SR


def extract_features(audio_path):

    y, sr = librosa.load(
        audio_path,
        sr=TARGET_SR
    )

    hop_length = 256

    rms = librosa.feature.rms(
        y=y,
        hop_length=hop_length
    )[0]

    pitch = librosa.yin(
        y,
        fmin=50,
        fmax=300,
        sr=sr,
        hop_length=hop_length
    )

    pitch[np.isnan(pitch)] = 0

    pitch = medfilt(
        pitch,
        kernel_size=11
    )

    times = librosa.frames_to_time(
        np.arange(len(rms)),
        sr=sr,
        hop_length=hop_length
    )

    pause_mask = rms < np.percentile(
        rms,
        15
    )

    delta_rms = np.abs(
        np.diff(rms, prepend=rms[0])
    )

    cps = np.convolve(
        delta_rms,
        np.ones(20) / 20,
        mode="same"
    )

    return {
        "rms": rms.tolist(),
        "pitch": pitch.tolist(),
        "times": times.tolist(),
        "pause_mask": pause_mask.tolist(),
        "cps": cps.tolist()
    }

