"""Minimal numpy-only synthesizer: renders NoteEvents to audio without any
external soundfont/VST dependency."""
import numpy as np

from arranger import DRUM_HIHAT, DRUM_KICK, DRUM_SNARE, NoteEvent


def midi_to_freq(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def _envelope(n: int, attack: float, decay: float, sustain: float, release: float, sr: int) -> np.ndarray:
    a = int(attack * sr)
    d = int(decay * sr)
    r = int(release * sr)
    s = max(n - a - d - r, 0)
    env = np.concatenate(
        [
            np.linspace(0, 1, max(a, 1), endpoint=False),
            np.linspace(1, sustain, max(d, 1), endpoint=False),
            np.full(s, sustain),
            np.linspace(sustain, 0, max(r, 1)),
        ]
    )
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    return env[:n]


def synth_bass(freq: float, duration: float, sr: int, velocity: float) -> np.ndarray:
    n = max(int(duration * sr), 1)
    t = np.arange(n) / sr
    wave = 0.6 * np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    wave += 0.1 * np.sign(np.sin(2 * np.pi * freq * t))
    env = _envelope(n, attack=0.005, decay=0.08, sustain=0.75, release=min(0.15, duration * 0.4), sr=sr)
    return wave * env * velocity


def synth_guitar(freq: float, duration: float, sr: int, velocity: float) -> np.ndarray:
    n = max(int(duration * sr), 1)
    t = np.arange(n) / sr
    wave = np.zeros(n)
    for i, amp in enumerate([1.0, 0.5, 0.3, 0.15, 0.08], start=1):
        wave += amp * np.sin(2 * np.pi * freq * i * t)
    wave /= sum([1.0, 0.5, 0.3, 0.15, 0.08])
    env = _envelope(n, attack=0.003, decay=0.15, sustain=0.35, release=min(0.2, duration * 0.5), sr=sr)
    return wave * env * velocity


def synth_kick(duration: float, sr: int, velocity: float) -> np.ndarray:
    n = max(int(max(duration, 0.15) * sr), 1)
    t = np.arange(n) / sr
    freq_env = 150 * np.exp(-t * 25) + 45
    phase = 2 * np.pi * np.cumsum(freq_env) / sr
    wave = np.sin(phase)
    amp_env = np.exp(-t * 18)
    click = np.random.randn(n) * np.exp(-t * 400) * 0.3
    return (wave * amp_env + click) * velocity


def synth_snare(duration: float, sr: int, velocity: float) -> np.ndarray:
    n = max(int(max(duration, 0.1) * sr), 1)
    t = np.arange(n) / sr
    noise = np.random.randn(n)
    amp_env = np.exp(-t * 22)
    tone = 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return (noise * 0.6 * amp_env + tone) * velocity


def synth_hihat(duration: float, sr: int, velocity: float) -> np.ndarray:
    n = max(int(max(duration, 0.05) * sr), 1)
    t = np.arange(n) / sr
    noise = np.random.randn(n)
    b = np.diff(noise, prepend=0)  # crude high-pass to brighten the noise
    amp_env = np.exp(-t * 60)
    return b * amp_env * velocity * 0.5


def render_track(events: list[NoteEvent], sr: int, total_samples: int) -> np.ndarray:
    out = np.zeros(total_samples, dtype=np.float64)
    for ev in events:
        if ev.instrument == "drums":
            if ev.drum_type == DRUM_KICK:
                snippet = synth_kick(ev.duration, sr, ev.velocity)
            elif ev.drum_type == DRUM_SNARE:
                snippet = synth_snare(ev.duration, sr, ev.velocity)
            elif ev.drum_type == DRUM_HIHAT:
                snippet = synth_hihat(ev.duration, sr, ev.velocity)
            else:
                continue
        elif ev.instrument == "bass":
            snippet = synth_bass(midi_to_freq(ev.midi), ev.duration, sr, ev.velocity)
        elif ev.instrument == "guitar":
            snippet = synth_guitar(midi_to_freq(ev.midi), ev.duration, sr, ev.velocity)
        else:
            continue

        start_sample = int(ev.start * sr)
        end_sample = start_sample + len(snippet)
        if start_sample >= total_samples:
            continue
        end_sample = min(end_sample, total_samples)
        out[start_sample:end_sample] += snippet[: end_sample - start_sample]

    peak = np.max(np.abs(out)) if out.size else 0.0
    if peak > 0.98:
        out = out / peak * 0.98
    return out
