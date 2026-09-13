"""End-to-end pipeline: audio file -> arranged mix + individual stems."""
from dataclasses import dataclass

import numpy as np

from arranger import generate_arrangement
from audio_analysis import analyze
from mixer import mix, write_wav
from synth import render_track

GENRES = ["rock", "ballad", "bossa"]


@dataclass
class ArrangeResult:
    sr: int
    tempo: float
    chords: list[str]
    mix: np.ndarray
    stems: dict[str, np.ndarray]
    original: np.ndarray


def run(path: str, genre: str, levels: dict[str, float] | None = None) -> ArrangeResult:
    analysis = analyze(path)
    total_samples = len(analysis.y)

    note_tracks = generate_arrangement(analysis.chords, genre)
    stems = {
        name: render_track(events, analysis.sr, total_samples)
        for name, events in note_tracks.items()
    }

    final_mix = mix(analysis.y, stems, levels)

    return ArrangeResult(
        sr=analysis.sr,
        tempo=analysis.tempo,
        chords=[c.label for c in analysis.chords],
        mix=final_mix,
        stems=stems,
        original=analysis.y,
    )


def run_and_save(path: str, genre: str, out_path: str, levels: dict[str, float] | None = None) -> ArrangeResult:
    result = run(path, genre, levels)
    write_wav(out_path, result.mix, result.sr)
    return result
