"""Rule-based accompaniment generator: turns detected chords into note events
for bass, guitar and drums, using per-genre pattern templates."""
from dataclasses import dataclass

from audio_analysis import Chord

DRUM_KICK = "kick"
DRUM_SNARE = "snare"
DRUM_HIHAT = "hihat"


@dataclass
class NoteEvent:
    start: float
    duration: float
    velocity: float  # 0-1
    instrument: str
    midi: int | None = None  # pitched instruments
    drum_type: str | None = None  # drum instrument


def _midi(pc: int, octave: int) -> int:
    return pc + 12 * (octave + 1)


def _chord_tone(chord: Chord, degree: str, octave: int) -> int:
    third = 3 if chord.is_minor else 4
    offsets = {"root": 0, "third": third, "fifth": 7, "octave": 12}
    return _midi(chord.root_pc, octave) + offsets[degree]


# Each pattern step: (beat_offset, duration_beats, degree_or_drum, velocity)
GENRES: dict[str, dict] = {
    "rock": {
        "bass_octave": 2,
        "guitar_octave": 3,
        "bass": [(0.0, 2.0, "root", 0.9), (2.0, 1.0, "fifth", 0.8), (3.0, 1.0, "root", 0.8)],
        "guitar": [(b, 1.0, "power", 0.75) for b in range(4)],
        "drums": (
            [(0.0, 0.5, DRUM_KICK, 1.0), (2.0, 0.5, DRUM_KICK, 0.9)]
            + [(1.0, 0.5, DRUM_SNARE, 0.95), (3.0, 0.5, DRUM_SNARE, 0.95)]
            + [(b * 0.5, 0.5, DRUM_HIHAT, 0.5 if b % 2 == 0 else 0.35) for b in range(8)]
        ),
    },
    "ballad": {
        "bass_octave": 2,
        "guitar_octave": 3,
        "bass": [(0.0, 4.0, "root", 0.6)],
        "guitar": [
            (0.0, 1.0, "root", 0.5),
            (1.0, 1.0, "third", 0.45),
            (2.0, 1.0, "fifth", 0.45),
            (3.0, 1.0, "octave", 0.45),
        ],
        "drums": (
            [(0.0, 0.5, DRUM_KICK, 0.6)]
            + [(2.0, 0.5, DRUM_SNARE, 0.55)]
            + [(b * 1.0, 0.5, DRUM_HIHAT, 0.3) for b in range(4)]
        ),
    },
    "bossa": {
        "bass_octave": 2,
        "guitar_octave": 3,
        "bass": [(0.0, 1.5, "root", 0.7), (1.5, 1.0, "fifth", 0.6), (3.0, 1.0, "root", 0.6)],
        "guitar": [
            (0.0, 0.75, "power", 0.55),
            (0.75, 0.75, "power", 0.4),
            (1.5, 1.0, "power", 0.5),
            (3.0, 1.0, "power", 0.45),
        ],
        "drums": (
            [(0.0, 0.5, DRUM_KICK, 0.7), (1.5, 0.5, DRUM_KICK, 0.55)]
            + [(2.0, 0.5, DRUM_SNARE, 0.5), (3.5, 0.5, DRUM_SNARE, 0.45)]
            + [(b * 0.5, 0.5, DRUM_HIHAT, 0.4) for b in range(8)]
        ),
    },
}


def generate_arrangement(chords: list[Chord], genre: str) -> dict[str, list[NoteEvent]]:
    if genre not in GENRES:
        raise ValueError(f"Unknown genre: {genre}. Options: {list(GENRES)}")
    tpl = GENRES[genre]
    tracks: dict[str, list[NoteEvent]] = {"bass": [], "guitar": [], "drums": []}

    for chord in chords:
        bar_len = chord.end - chord.start
        beat_len = bar_len / 4.0

        for beat_offset, dur_beats, degree, vel in tpl["bass"]:
            start = chord.start + beat_offset * beat_len
            midi = _chord_tone(chord, degree, tpl["bass_octave"])
            tracks["bass"].append(NoteEvent(start, dur_beats * beat_len, vel, "bass", midi=midi))

        for beat_offset, dur_beats, degree, vel in tpl["guitar"]:
            start = chord.start + beat_offset * beat_len
            dur = dur_beats * beat_len
            if degree == "power":
                root_midi = _chord_tone(chord, "root", tpl["guitar_octave"])
                fifth_midi = _chord_tone(chord, "fifth", tpl["guitar_octave"])
                tracks["guitar"].append(NoteEvent(start, dur, vel, "guitar", midi=root_midi))
                tracks["guitar"].append(NoteEvent(start, dur, vel * 0.85, "guitar", midi=fifth_midi))
            else:
                midi = _chord_tone(chord, degree, tpl["guitar_octave"])
                tracks["guitar"].append(NoteEvent(start, dur, vel, "guitar", midi=midi))

        for beat_offset, dur_beats, drum_type, vel in tpl["drums"]:
            start = chord.start + beat_offset * beat_len
            tracks["drums"].append(
                NoteEvent(start, dur_beats * beat_len, vel, "drums", drum_type=drum_type)
            )

    return tracks
