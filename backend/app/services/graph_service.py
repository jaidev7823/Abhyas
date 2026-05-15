def build_reference_payload(
    features,
    words
):

    return {
        "times": features["times"],
        "rms": features["rms"],
        "pitch": features["pitch"],
        "pause_mask": features["pause_mask"],
        "cps": features["cps"],
        "words": words
    }

