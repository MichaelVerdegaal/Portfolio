"""WebP poster export for a single animation frame."""

from collections.abc import Callable
from pathlib import Path

from matplotlib.figure import Figure
from PIL import Image

from ..config import COLOR_BG, DPI, TARGET_HEIGHT, TARGET_WIDTH


def save_poster(
    fig: Figure,
    update: Callable[[int], object],
    frame: int,
    path: Path,
) -> None:
    """Save a WebP poster matching the requested frame.

    The PNG is written at figure DPI and downscaled with Pillow rather than
    saved at a lower DPI directly, because the label collection bakes in
    fig.dpi/72 at construction time and would not rescale with savefig.

    Args:
        fig: The figure to capture.
        update: Callback that advances the scene to the desired frame.
        frame: Frame index to render for the poster.
        path: Output .webp path.
    """
    update(frame)

    png_path = path.with_suffix(".png")
    fig.savefig(png_path, dpi=DPI, facecolor=COLOR_BG)
    with Image.open(png_path) as img:
        resized = img.convert("RGB").resize(
            (TARGET_WIDTH, TARGET_HEIGHT), Image.LANCZOS
        )
        resized.save(path, format="WEBP", quality=82, method=6)
    png_path.unlink()
