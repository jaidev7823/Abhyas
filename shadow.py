import gradio as gr
import librosa
import numpy as np
import matplotlib.pyplot as plt

from scipy.signal import medfilt
from sklearn.preprocessing import MinMaxScaler

TARGET_SR = 16000


# =========================================================
# FEATURE EXTRACTION
# =========================================================
def extract_features(audio_path, sr=TARGET_SR):

    y, sr = librosa.load(audio_path, sr=sr)

    hop_length = 256

    # RMS
    rms = librosa.feature.rms(
        y=y,
        hop_length=hop_length
    )[0]

    # Pitch
    pitch = librosa.yin(
        y,
        fmin=50,
        fmax=300,
        sr=sr,
        hop_length=hop_length
    )

    pitch[np.isnan(pitch)] = 0

    pitch = medfilt(pitch, kernel_size=11)

    # Time axis
    times = librosa.frames_to_time(
        np.arange(len(rms)),
        sr=sr,
        hop_length=hop_length
    )

    # Pause detection
    pause_mask = rms < np.percentile(rms, 15)

    # Speaking speed approximation
    delta_rms = np.abs(np.diff(rms, prepend=rms[0]))

    cps = np.convolve(
        delta_rms,
        np.ones(20) / 20,
        mode="same"
    )

    return {
        "rms": rms,
        "pitch": pitch,
        "times": times,
        "pause_mask": pause_mask,
        "cps": cps
    }


# =========================================================
# NORMALIZATION
# =========================================================
def normalize_feature(feature):
    scaler = MinMaxScaler()

    feature = feature.reshape(-1, 1)

    normalized = scaler.fit_transform(feature)

    return normalized.flatten()


# =========================================================
# DTW ALIGNMENT
# =========================================================
def dtw_align(master, user):
    """
    Align user sequence to master sequence
    using DTW.
    """

    D, wp = librosa.sequence.dtw(
        X=master.reshape(1, -1),
        Y=user.reshape(1, -1),
        metric="euclidean"
    )

    wp = np.array(wp[::-1])

    aligned_master = master[wp[:, 0]]
    aligned_user = user[wp[:, 1]]

    distance = D[-1, -1]

    return aligned_master, aligned_user, distance


# =========================================================
# MAIN COMPARISON
# =========================================================
def compare_audio(master_audio, user_audio):

    if master_audio is None or user_audio is None:
        return "Upload both audio files.", None

    # =====================================================
    # EXTRACT FEATURES
    # =====================================================

    master = extract_features(master_audio)
    user = extract_features(user_audio)

    # =====================================================
    # NORMALIZE FOR DTW
    # =====================================================

    master_rms_norm = normalize_feature(master["rms"])
    user_rms_norm = normalize_feature(user["rms"])

    master_pitch_norm = normalize_feature(master["pitch"])
    user_pitch_norm = normalize_feature(user["pitch"])

    # =====================================================
    # DTW SCORE ONLY
    # =====================================================

    _, _, rms_distance = dtw_align(
        master_rms_norm,
        user_rms_norm
    )

    _, _, pitch_distance = dtw_align(
        master_pitch_norm,
        user_pitch_norm
    )

    total_distance = rms_distance + pitch_distance

    score = 100 * np.exp(-total_distance / 200)

    score = np.clip(score, 0, 100)

    score_text = f"{score:.2f}% Match"

    # =====================================================
    # HUMAN FRIENDLY VISUALIZATION
    # =====================================================

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(14, 10),
        sharex=False
    )

    # =====================================================
    # GRAPH 1 — RMS
    # =====================================================

    axes[0].plot(
        master["times"],
        master["rms"],
        label="Master RMS"
    )

    axes[0].plot(
        user["times"],
        user["rms"],
        label="User RMS",
        linestyle="--"
    )

    axes[0].set_title("Volume / RMS Over Time")
    axes[0].legend()
    axes[0].grid(True)

    # =====================================================
    # GRAPH 2 — PITCH
    # =====================================================

    axes[1].plot(
        master["times"],
        master["pitch"],
        label="Master Pitch"
    )

    axes[1].plot(
        user["times"],
        user["pitch"],
        label="User Pitch",
        linestyle="--"
    )

    axes[1].set_title("Pitch Over Time")
    axes[1].legend()
    axes[1].grid(True)

    # =====================================================
    # GRAPH 3 — SPEAKING SPEED
    # =====================================================

    axes[2].plot(
        master["times"],
        master["cps"],
        label="Master Speech Speed"
    )

    axes[2].plot(
        user["times"],
        user["cps"],
        label="User Speech Speed",
        linestyle="--"
    )

    axes[2].set_title("Speech Activity / Speed")
    axes[2].legend()
    axes[2].grid(True)

    # =====================================================
    # PAUSE VISUALIZATION
    # =====================================================

    for ax in axes:

        for i in range(len(master["times"]) - 1):

            if master["pause_mask"][i]:

                ax.axvspan(
                    master["times"][i],
                    master["times"][i + 1],
                    color="red",
                    alpha=0.08
                )

    plt.tight_layout()

    return score_text, fig


# =========================================================
# =========================================================
with gr.Blocks() as app:

    gr.Markdown("# Interactive Speech Shadowing Coach")

    with gr.Row():

        master_audio = gr.Audio(
            label="Upload Master Audio Chunk",
            type="filepath"
        )

    with gr.Row():

        user_audio = gr.Audio(
            sources=["microphone"],
            label="Record Your Attempt",
            type="filepath"
        )

    score_btn = gr.Button("Score My Attempt")

    with gr.Row():

        score_output = gr.Textbox(
            label="Overall Match Score"
        )

    with gr.Row():

        plot_output = gr.Plot(
            label="Metric Breakdown"
        )

    score_btn.click(
        fn=compare_audio,
        inputs=[master_audio, user_audio],
        outputs=[score_output, plot_output]
    )


# =========================================================
# LAUNCH
# =========================================================
app.launch(debug=True)