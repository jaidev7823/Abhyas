import numpy as np


def normalize(feature):
    arr = np.array(feature, dtype=np.float64)
    mn, mx = arr.min(), arr.max()
    if mx - mn < 1e-10:
        return np.zeros_like(arr)
    return (arr - mn) / (mx - mn)


def dtw_distance(master, user):
    m, u = np.array(master), np.array(user)
    D = np.full((len(m) + 1, len(u) + 1), np.inf)
    D[0, 0] = 0
    for i in range(1, len(m) + 1):
        for j in range(1, len(u) + 1):
            cost = abs(float(m[i - 1]) - float(u[j - 1]))
            D[i, j] = cost + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return D[-1, -1] / max(len(m), len(u))


def score_from_distance(dist):
    score = 100 * np.exp(-dist / 0.5)
    return round(float(np.clip(score, 0, 100)), 1)


def calculate_score(master_features, user_features):
    m_rms = normalize(master_features["rms"])
    u_rms = normalize(user_features["rms"])
    m_pitch = normalize(master_features["pitch"])
    u_pitch = normalize(user_features["pitch"])
    m_cps = normalize(master_features["cps"])
    u_cps = normalize(user_features["cps"])

    m_dur = master_features.get("duration", 1)
    u_dur = user_features.get("duration", 1)
    dur_ratio = min(m_dur, u_dur) / max(m_dur, u_dur)
    timing = round(float(dur_ratio * 100), 1)

    pitch_dist = dtw_distance(m_pitch, u_pitch)
    pitch = score_from_distance(pitch_dist)

    rhythm_dist = dtw_distance(m_rms, u_rms)
    rhythm = score_from_distance(rhythm_dist)

    pacing_dist = dtw_distance(m_cps, u_cps)
    pacing = score_from_distance(pacing_dist)

    overall = round(
        timing * 0.15 + pitch * 0.35 + rhythm * 0.25 + pacing * 0.25, 1
    )

    return {
        "overall": overall,
        "timing": timing,
        "pitch": pitch,
        "rhythm": rhythm,
        "pacing": pacing,
    }
