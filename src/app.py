"""FastAPI backend that serves the portfolio hero page and static assets."""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src import config

app = FastAPI()
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


def _static_file(name: str) -> FileResponse:
    return FileResponse(config.STATIC_DIR / name)


@app.get("/")
def index() -> FileResponse:
    """Serve the hero page at the root path."""
    return _static_file("index.html")


# Well-known files that crawlers and browsers expect at the site root rather
# than under /static.
@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return _static_file("favicon.ico")


@app.get("/robots.txt", include_in_schema=False)
def robots() -> FileResponse:
    return _static_file("robots.txt")


@app.get("/llms.txt", include_in_schema=False)
def llms() -> FileResponse:
    return _static_file("llms.txt")
