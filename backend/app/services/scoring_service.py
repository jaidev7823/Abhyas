import numpy as np
import librosa

from sklearn.preprocessing import MinMaxScaler


def normalize_feature(feature):

    scaler = MinMaxScaler()

    feature = np.array(feature).reshape(-1, 1)

    normalized = scaler.fit_transform(feature)

    return normalized.flatten()


def dtw_distance(master, user):

    D, wp = librosa.sequence.dtw(
        X=master.reshape(1, -1),
        Y=user.reshape(1, -1),
        metric="euclidean"
    )

    return D[-1, -1]


def calculate_score(master_features, user_features):

    master_rms = normalize_feature(
        master_features["rms"]
    )

    user_rms = normalize_feature(
        user_features["rms"]
    )

    master_pitch = normalize_feature(
        master_features["pitch"]
    )

    user_pitch = normalize_feature(
        user_features["pitch"]
    )

    rms_distance = dtw_distance(
        master_rms,
        user_rms
    )

    pitch_distance = dtw_distance(
        master_pitch,
        user_pitch
    )

    total_distance = rms_distance + pitch_distance

    score = 100 * np.exp(
        -total_distance / 200
    )

    score = np.clip(
        score,
        0,
        100
    )

    return round(float(score), 2)

