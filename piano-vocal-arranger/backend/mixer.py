"""Combine the original piano+vocal audio with the synthesized accompaniment
stems into one mastered mix."""
import numpy as np
import soundfile as sf

DEFAULT_LEVELS = {"original": 1.0, "bass": 0.9, "guitar": 0.7, "drums": 0.8}


def mix(
    original: np.ndarray,
    stems: dict[str, np.ndarray],
    levels: dict[str, float] | None = None,
) -> np.ndarray:
    levels = {**DEFAULT_LEVELS, **(levels or {})}
    total = original.astype(np.float64) * levels.get("original", 1.0)
    for name, audio in stems.items():
        total = total + audio * levels.get(name, 1.0)

    peak = np.max(np.abs(total))
    if peak > 0.98:
        total = total / peak * 0.98
    return total


def write_wav(path: str, audio: np.ndarray, sr: int) -> None:
    sf.write(path, audio.astype(np.float32), sr, subtype="PCM_16")
