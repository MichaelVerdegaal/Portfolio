"""FastAPI backend that serves the portfolio hero page and static assets."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
STATIC.mkdir(exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index() -> FileResponse:
    """Serve the hero page at the root path."""
    return FileResponse(STATIC / "index.html")


@app.get("/video/{filename}")
def video(request: Request, filename: str) -> FileResponse:
    """Serve an MP4 with byte-range support so browsers can stream it."""
    if filename not in {"hero-intro.mp4", "hero-loop.mp4"}:
        raise FileNotFoundError(filename)
    path = STATIC / filename
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=filename,
        content_disposition_type="inline",
    )
