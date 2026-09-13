"""FastAPI server for the piano+vocal -> full band arranger."""
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pipeline import GENRES, run_and_save

app = FastAPI(title="Piano+Vocal Arranger")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/api/genres")
def list_genres():
    return {"genres": GENRES}


@app.post("/api/arrange")
async def arrange(
    file: UploadFile = File(...),
    genre: str = Form("rock"),
    bass_level: float = Form(0.9),
    guitar_level: float = Form(0.7),
    drums_level: float = Form(0.8),
    original_level: float = Form(1.0),
):
    if genre not in GENRES:
        raise HTTPException(400, f"genre must be one of {GENRES}")

    tmpdir = tempfile.mkdtemp(prefix="arranger_")
    in_path = Path(tmpdir) / (file.filename or "input.wav")
    out_path = Path(tmpdir) / "arranged.wav"

    with open(in_path, "wb") as f:
        f.write(await file.read())

    levels = {
        "original": original_level,
        "bass": bass_level,
        "guitar": guitar_level,
        "drums": drums_level,
    }
    try:
        result = run_and_save(str(in_path), genre, str(out_path), levels)
    except Exception as exc:  # surface analysis/synthesis errors to the client
        raise HTTPException(500, f"arrangement failed: {exc}") from exc

    return FileResponse(
        out_path,
        media_type="audio/wav",
        filename="arranged.wav",
        headers={
            "X-Tempo": str(round(result.tempo, 1)),
            "X-Chords": ",".join(result.chords[:32]),
        },
    )


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
