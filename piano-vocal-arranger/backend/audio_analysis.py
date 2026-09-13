"""Analyze a piano+vocal audio file: tempo, beat grid, and per-bar chords."""
from dataclasses import dataclass

import librosa
import numpy as np

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class Chord:
    start: float
    end: float
    root_pc: int  # pitch class 0-11 (0 = C)
    is_minor: bool

    @property
    def label(self) -> str:
        return f"{NOTE_NAMES[self.root_pc]}{'m' if self.is_minor else ''}"


@dataclass
class Analysis:
    y: np.ndarray
    sr: int
    tempo: float
    beat_times: np.ndarray
    bar_times: np.ndarray  # bar boundary timestamps (every 4 beats)
    chords: list[Chord]
    duration: float


def _chord_templates() -> tuple[np.ndarray, list[tuple[int, bool]]]:
    """Build 24 chroma templates (12 major + 12 minor triads)."""
    templates = []
    labels = []
    for root in range(12):
        for is_minor in (False, True):
            third = 3 if is_minor else 4
            template = np.zeros(12)
            template[root] = 1.0
            template[(root + third) % 12] = 0.75
            template[(root + 7) % 12] = 0.85
            templates.append(template)
            labels.append((root, is_minor))
    return np.array(templates), labels


_TEMPLATES, _TEMPLATE_LABELS = _chord_templates()


def _estimate_chord(chroma_vec: np.ndarray) -> tuple[int, bool]:
    norm = np.linalg.norm(chroma_vec)
    if norm < 1e-6:
        return 0, False
    v = chroma_vec / norm
    sims = _TEMPLATES @ v / (np.linalg.norm(_TEMPLATES, axis=1) + 1e-9)
    best = int(np.argmax(sims))
    return _TEMPLATE_LABELS[best]


def analyze(path: str) -> Analysis:
    y, sr = librosa.load(path, sr=44100, mono=True)
    duration = len(y) / sr

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    tempo = float(np.atleast_1d(tempo)[0])
    if tempo <= 0:
        tempo = 120.0
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    if len(beat_times) < 2:
        beat_interval = 60.0 / tempo
        beat_times = np.arange(0, duration, beat_interval)

    bar_times = beat_times[::4]
    if len(bar_times) == 0 or bar_times[0] > 0:
        bar_times = np.concatenate([[0.0], bar_times])
    if bar_times[-1] < duration:
        bar_times = np.concatenate([bar_times, [duration]])

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr)

    chords: list[Chord] = []
    for i in range(len(bar_times) - 1):
        start, end = bar_times[i], bar_times[i + 1]
        mask = (chroma_times >= start) & (chroma_times < end)
        if not np.any(mask):
            root_pc, is_minor = (chords[-1].root_pc, chords[-1].is_minor) if chords else (0, False)
        else:
            avg_chroma = chroma[:, mask].mean(axis=1)
            root_pc, is_minor = _estimate_chord(avg_chroma)
        chords.append(Chord(start=start, end=end, root_pc=root_pc, is_minor=is_minor))

    return Analysis(
        y=y,
        sr=sr,
        tempo=tempo,
        beat_times=beat_times,
        bar_times=bar_times,
        chords=chords,
        duration=duration,
    )
