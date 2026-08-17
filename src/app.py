"""FastAPI backend that serves the portfolio hero page and static assets."""

from fastapi.applications import FastAPI


from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src import config

config.STATIC_DIR.mkdir(exist_ok=True)

app: FastAPI = FastAPI()
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    """Serve the hero page at the root path."""
    return FileResponse(config.STATIC_DIR / "index.html")


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse("/favicon.ico")