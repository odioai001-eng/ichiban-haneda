"""Command-line entry point: arrange a local audio file without the web server."""
import argparse

from pipeline import GENRES, run_and_save


def main() -> None:
    parser = argparse.ArgumentParser(description="Arrange a piano+vocal audio file into a full band mix.")
    parser.add_argument("input", help="path to the piano+vocal audio file")
    parser.add_argument("--genre", choices=GENRES, default="rock")
    parser.add_argument("--out", default="arranged.wav")
    args = parser.parse_args()

    result = run_and_save(args.input, args.genre, args.out)
    print(f"tempo: {result.tempo:.1f} BPM")
    print(f"chords: {' '.join(result.chords)}")
    print(f"saved: {args.out}")


if __name__ == "__main__":
    main()
