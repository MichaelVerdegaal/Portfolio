"""Export hero intro/loop MP4s and a poster for the portfolio site."""

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.animation import FFMpegWriter, FuncAnimation
from numpy.typing import NDArray

from src.animate import tween_history
from src.graphview import GraphView, load_graph_data
from src.layout import AXIS_MAX, AXIS_MIN, layout_function
from src.mpl_utils import COLOR_BG, create_figure_3d

FPS = 60
ORBIT_SECONDS = 20
LOOP_FRAMES = FPS * ORBIT_SECONDS  # 1200, exactly one 360-degree turn
DEG_PER_FRAME = 360 / LOOP_FRAMES  # 0.3 degrees per frame
INTRO_FRAMES = 450  # 7.5s layout convergence
ELEV0 = 30.0
AZIM0 = 100.0

# Export at 2x 1080p (3840x2160) and let ffmpeg downsample.
# Build the figure at this dpi and pass the same dpi to anim.save to keep
# TextPath glyph scales consistent.
FIGSIZE = (38.4, 21.6)
DPI = 100
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
CRF = 18


def _check_ffmpeg() -> None:
    """Raise FileNotFoundError if ffmpeg is not on PATH."""
    if shutil.which("ffmpeg") is None:
        raise FileNotFoundError("ffmpeg is not on PATH; install ffmpeg to export video")


def _tweened_positions(intro_frames: int) -> NDArray[np.float64]:
    """Build a layout history: random start -> ForceAtlas2 target."""
    fig, ax = create_figure_3d(figsize=FIGSIZE, dpi=DPI)
    graph_data = load_graph_data()
    view = GraphView(
        fig,
        ax,
        nx.DiGraph(graph_data),
        axis_lim=(AXIS_MIN, AXIS_MAX),
        spawn_margin=10,
        is_3d=True,
    )

    # Framing: zoom is the correct lever; focal_length only affects depth.
    ax.set_box_aspect((1, 1, 1), zoom=1.4)
    ax.set_proj_type("persp", focal_length=0.25)

    start_layout = view.pos.copy()
    target_layout = layout_function(view, is_3d=True)
    history = tween_history(start_layout, target_layout, intro_frames)

    plt.close(fig)
    return history


def intro_azim(frame: int) -> float:
    """Azimuth that lands one step before AZIM0 at the final intro frame."""
    return (AZIM0 - DEG_PER_FRAME * (INTRO_FRAMES - frame)) % 360


def loop_azim(frame: int) -> float:
    """Azimuth that completes exactly one turn over the loop."""
    return (AZIM0 + DEG_PER_FRAME * frame) % 360


def render_clip(
    history: NDArray[np.float64],
    path: Path,
    frames: int,
    pos_for: Callable[[int], NDArray[np.float64]],
    azim_for: Callable[[int], float],
) -> None:
    """Render a clip to MP4 with web-safe H.264 encoding.

    Args:
        history: The full layout history from tween_history.
        path: Output file path.
        frames: Number of frames to render.
        pos_for: Maps frame index to an (N, 3) position array.
        azim_for: Maps frame index to a camera azimuth in degrees.

    Raises:
        FileNotFoundError: If ffmpeg is not on PATH.
    """
    _check_ffmpeg()

    fig, ax = create_figure_3d(figsize=FIGSIZE, dpi=DPI)
    graph_data = load_graph_data()
    view = GraphView(
        fig,
        ax,
        nx.DiGraph(graph_data),
        axis_lim=(AXIS_MIN, AXIS_MAX),
        spawn_margin=10,
        is_3d=True,
    )
    ax.set_box_aspect((1, 1, 1), zoom=1.4)
    ax.set_proj_type("persp", focal_length=0.25)

    scatter, edges, labels = view.get_artists()

    def animate(frame: int) -> list:
        pos = pos_for(frame)
        view.pos = pos
        ax.view_init(elev=ELEV0, azim=azim_for(frame))
        return [scatter, edges, labels]

    writer = FFMpegWriter(
        fps=FPS,
        codec="libx264",
        extra_args=[
            "-crf",
            str(CRF),
            "-preset",
            "slow",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
        ],
    )

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "raw.mp4"
        anim = FuncAnimation(
            fig,
            animate,
            frames=frames,
            interval=1000 // FPS,
            repeat=False,
            blit=False,
            cache_frame_data=False,
        )
        anim.save(str(tmp_path), writer=writer, dpi=DPI)

        # Downsample 2x render to final 1080p with lanczos.
        scale_filter = (
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(tmp_path),
                "-vf",
                scale_filter,
                "-c:v",
                "libx264",
                "-crf",
                str(CRF),
                "-preset",
                "slow",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-an",
                str(path),
            ],
            check=True,
        )

    plt.close(fig)


def save_poster(path: Path, history: NDArray[np.float64]) -> None:
    """Save a PNG poster from the converged layout at AZIM0."""
    fig, ax = create_figure_3d(figsize=FIGSIZE, dpi=DPI)
    graph_data = load_graph_data()
    view = GraphView(
        fig,
        ax,
        nx.DiGraph(graph_data),
        axis_lim=(AXIS_MIN, AXIS_MAX),
        spawn_margin=10,
        is_3d=True,
    )
    ax.set_box_aspect((1, 1, 1), zoom=1.4)
    ax.set_proj_type("persp", focal_length=0.25)

    view.pos = history[-1]
    ax.view_init(elev=ELEV0, azim=AZIM0)
    fig.savefig(path, dpi=DPI, facecolor=COLOR_BG)
    plt.close(fig)


def main() -> None:
    """Render intro, loop, and poster into the static directory."""
    static_dir = Path(__file__).resolve().parent.parent / "static"
    static_dir.mkdir(exist_ok=True)

    history = _tweened_positions(INTRO_FRAMES)

    render_clip(
        history,
        static_dir / "hero-intro.mp4",
        INTRO_FRAMES,
        pos_for=lambda f: history[min(f, len(history) - 1)],
        azim_for=intro_azim,
    )

    render_clip(
        history,
        static_dir / "hero-loop.mp4",
        LOOP_FRAMES,
        pos_for=lambda f: history[-1],
        azim_for=loop_azim,
    )

    save_poster(static_dir / "hero-poster.png", history)


if __name__ == "__main__":
    main()
