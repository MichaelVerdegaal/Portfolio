"""FastAPI backend that serves the portfolio hero page and static assets."""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.config import STATIC_DIR

STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _static_file(name: str) -> FileResponse:
    return FileResponse(STATIC_DIR / name)


@app.get("/")
def index() -> FileResponse:
    """Serve the hero page at the root path."""
    return FileResponse(STATIC_DIR / "index.html")
