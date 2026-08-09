"""Export the looping hero orbit and its poster frame for the portfolio site."""

import shutil
from collections.abc import Callable
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.animation import FFMpegWriter, FuncAnimation
from matplotlib.artist import Artist
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.axes3d import Axes3D
from numpy.typing import NDArray
from PIL import Image

from src import config
from src.animate import tween_history
from src.graphview import GraphView, load_graph_data
from src.layout import layout_function
from src.mpl_utils import create_figure_3d

plt.switch_backend("Agg")


def _check_ffmpeg() -> None:
    """Raise FileNotFoundError if ffmpeg is not on PATH."""
    if shutil.which("ffmpeg") is None:
        raise FileNotFoundError("ffmpeg is not on PATH; install ffmpeg to export video")


def build_scene() -> tuple[Figure, Axes3D, GraphView]:
    """Build the export figure, axes and graph view.

    Camera framing and axis bounds come from create_figure_3d, so the export
    and the interactive preview stay in sync.

    Returns:
        The figure, its 3D axes, and the GraphView holding node positions.
    """
    fig, ax = create_figure_3d(figsize=config.FIGSIZE, dpi=config.DPI)
    view = GraphView(
        fig,
        ax,
        nx.DiGraph(load_graph_data()),
        axis_lim=(config.AXIS_MIN, config.AXIS_MAX),
        spawn_margin=config.SPAWN_MARGIN,
        is_3d=True,
    )
    return fig, ax, view


def intro_azim(frame: int) -> float:
    """Azimuth that lands one step before AZIM0 at the final intro frame.

    Unused while config.RENDER_INTRO is False. Kept for the project page.

    Args:
        frame: Frame index within the intro clip.

    Returns:
        The camera azimuth in degrees.
    """
    return (config.AZIM0 - config.DEG_PER_FRAME * (config.INTRO_FRAMES - frame)) % 360


def loop_azim(frame: int) -> float:
    """Azimuth that completes exactly one turn over the loop.

    Args:
        frame: Frame index within the loop clip.

    Returns:
        The camera azimuth in degrees.
    """
    return (config.AZIM0 + config.DEG_PER_FRAME * frame) % 360


def render_clip(
    fig: Figure,
    ax: Axes3D,
    view: GraphView,
    path: Path,
    frames: int,
    pos_for: Callable[[int], NDArray[np.float64]],
    azim_for: Callable[[int], float],
) -> None:
    """Render a clip to MP4 in a single ffmpeg pass.

    Frames are piped to ffmpeg at FIGSIZE * DPI and downscaled to the target
    resolution by the scale filter in the writer's extra_args, so there is no
    second encode.

    Args:
        fig: The figure to capture.
        ax: The 3D axes whose camera is driven per frame.
        view: The GraphView whose positions are set per frame.
        path: Output file path.
        frames: Number of frames to render.
        pos_for: Maps a frame index to an (N, 3) position array.
        azim_for: Maps a frame index to a camera azimuth in degrees.
    """

    def animate(frame: int) -> list[Artist]:
        view.pos = pos_for(frame)
        ax.view_init(elev=config.ELEV0, azim=azim_for(frame))
        return list(view.get_artists())

    writer = FFMpegWriter(
        fps=config.FPS,
        codec="libx264",
        extra_args=[
            "-vf",
            config.VIDEO_FILTERS,
            "-crf",
            str(config.CRF),
            "-preset",
            config.PRESET,
            "-tune",
            "animation",
            "-x264-params",
            "aq-mode=3",
            "-pix_fmt",
            "yuv420p",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-movflags",
            "+faststart",
            "-an",
        ],
    )

    anim = FuncAnimation(
        fig,
        animate,
        frames=frames,
        interval=1000 // config.FPS,
        repeat=False,
        blit=False,
        cache_frame_data=False,
    )
    anim.save(str(path), writer=writer, dpi=config.DPI)


def save_poster(
    fig: Figure,
    ax: Axes3D,
    view: GraphView,
    positions: NDArray[np.float64],
    path: Path,
) -> None:
    """Save a WebP poster matching the first frame of the loop.

    The PNG is written at figure DPI and downscaled with Pillow rather than
    saved at a lower DPI directly, because the label collection bakes in
    fig.dpi/72 at construction time and would not rescale with savefig.

    Args:
        fig: The figure to capture.
        ax: The 3D axes whose camera is set to the loop start.
        view: The GraphView whose positions are set to the converged layout.
        positions: The (N, 3) converged layout.
        path: Output .webp path.
    """
    view.pos = positions
    ax.view_init(elev=config.ELEV0, azim=config.AZIM0)

    png_path = path.with_suffix(".png")
    fig.savefig(png_path, dpi=config.DPI, facecolor=config.COLOR_BG)
    with Image.open(png_path) as img:
        resized = img.convert("RGB").resize(
            (config.TARGET_WIDTH, config.TARGET_HEIGHT), Image.LANCZOS
        )
        resized.save(path, format="WEBP", quality=82, method=6)
    png_path.unlink()


def main() -> None:
    """Render the hero loop and poster into the static directory."""
    _check_ffmpeg()
    config.STATIC_DIR.mkdir(exist_ok=True)

    fig, ax, view = build_scene()
    spawn_positions = view.pos.copy()
    final_positions = layout_function(view, is_3d=True)

    if config.RENDER_INTRO:
        history = tween_history(spawn_positions, final_positions, config.INTRO_FRAMES)
        render_clip(
            fig,
            ax,
            view,
            config.STATIC_DIR / "hero-intro.mp4",
            config.INTRO_FRAMES,
            pos_for=lambda frame: history[min(frame, len(history) - 1)],
            azim_for=intro_azim,
        )

    render_clip(
        fig,
        ax,
        view,
        config.STATIC_DIR / "hero-loop.mp4",
        config.LOOP_FRAMES,
        pos_for=lambda _: final_positions,
        azim_for=loop_azim,
    )

    save_poster(fig, ax, view, final_positions, config.STATIC_DIR / "hero-poster.webp")
    plt.close(fig)


if __name__ == "__main__":
    main()
