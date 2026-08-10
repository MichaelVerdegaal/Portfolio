"""Export the looping hero orbit and its poster frame for the portfolio site."""

import math
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

Camera = tuple[float, float, float]


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


def loop_azim(frame: int) -> float:
    """Azimuth oscillating around AZIM0, one cycle per loop.

    Args:
        frame: Frame index within the loop clip.

    Returns:
        The camera azimuth in degrees.
    """
    t = frame / config.LOOP_FRAMES
    return config.AZIM0 + config.AZIM_AMPLITUDE * math.sin(2 * math.pi * t)


def loop_elev(frame: int) -> float:
    """Elevation built from a first and third harmonic.

    The third harmonic and the phase offset keep the vertical motion from
    reading as a metronome synchronised with the azimuth sweep.

    Args:
        frame: Frame index within the loop clip.

    Returns:
        The camera elevation in degrees.
    """
    t = frame / config.LOOP_FRAMES
    return (
        config.ELEV0
        + config.ELEV_AMPLITUDE * math.sin(2 * math.pi * t + config.ELEV_PHASE)
        + config.ELEV_AMPLITUDE_3 * math.sin(2 * math.pi * 3 * t)
    )


def loop_roll(frame: int) -> float:
    """Camera roll on a second harmonic.

    Args:
        frame: Frame index within the loop clip.

    Returns:
        The camera roll in degrees.
    """
    t = frame / config.LOOP_FRAMES
    return config.ROLL_AMPLITUDE * math.sin(2 * math.pi * 2 * t + config.ROLL_PHASE)


def loop_camera(frame: int) -> Camera:
    """Full camera orientation for a loop frame.

    Args:
        frame: Frame index within the loop clip.

    Returns:
        An (elev, azim, roll) tuple in degrees.
    """
    return (loop_elev(frame), loop_azim(frame), loop_roll(frame))


def intro_azim(frame: int) -> float:
    """Azimuth that lands one step before AZIM0 at the final intro frame.

    Args:
        frame: Frame index within the intro clip.

    Returns:
        The camera azimuth in degrees.
    """
    return (config.AZIM0 - config.DEG_PER_FRAME * (config.INTRO_FRAMES - frame)) % 360


def intro_camera(frame: int) -> Camera:
    """Camera orientation for the intro clip.

    Unused while config.RENDER_INTRO is False. Kept for the project page.

    Args:
        frame: Frame index within the intro clip.

    Returns:
        An (elev, azim, roll) tuple in degrees.
    """
    return (config.ELEV0, intro_azim(frame), 0.0)


def drift_field(node_count: int) -> Callable[[int], NDArray[np.float64]]:
    """Build a per-node positional drift that returns exactly to its start.

    Each node gets an independent random phase and amplitude scale per
    harmonic, so nodes wander out of step with each other while the whole
    field still closes at frame LOOP_FRAMES.

    Args:
        node_count: Number of nodes in the graph.

    Returns:
        A function mapping a frame index to an (N, 3) offset in axis units.
    """
    rng = np.random.default_rng(config.DRIFT_SEED)
    harmonics = np.array(config.DRIFT_HARMONICS, dtype=np.float64)[:, None, None]
    shape = (len(config.DRIFT_HARMONICS), node_count, 3)
    phases = rng.uniform(0.0, 1.0, shape)
    scales = rng.uniform(0.4, 1.0, shape)
    amplitudes = np.array(config.DRIFT_AMPLITUDES)[:, None, None] * scales

    def offset(frame: int) -> NDArray[np.float64]:
        t = frame / config.LOOP_FRAMES
        return (amplitudes * np.sin(2 * np.pi * (harmonics * t + phases))).sum(axis=0)

    return offset


def breath_field(node_count: int) -> Callable[[int], NDArray[np.float64]]:
    """Build a per-node opacity field that closes at the loop boundary.

    Each node gets a fixed whole-number harmonic and phase. The waveform uses
    a short smooth ramp between its dim and bright plateaus, which keeps the
    opacity change readable without making the graph flicker.

    Args:
        node_count: Number of nodes in the graph.

    Returns:
        A function mapping a frame index to an (N,) alpha multiplier array.
    """
    rng = np.random.default_rng(config.BREATH_SEED)
    harmonics = rng.choice(config.BREATH_HARMONICS, size=node_count).astype(float)
    phases = rng.uniform(0.0, 1.0, node_count)
    ramp = 0.5 * config.BREATH_DUTY

    def alpha(frame: int) -> NDArray[np.float64]:
        t = frame / config.LOOP_FRAMES
        phase = (harmonics * t + phases) % 1.0
        pulse = np.zeros(node_count)

        rising = phase < ramp
        rising_t = phase[rising] / ramp
        pulse[rising] = rising_t**2 * (3.0 - 2.0 * rising_t)

        high = (phase >= ramp) & (phase < 0.5)
        pulse[high] = 1.0

        falling = (phase >= 0.5) & (phase < 0.5 + ramp)
        falling_t = (phase[falling] - 0.5) / ramp
        pulse[falling] = 1.0 - falling_t**2 * (3.0 - 2.0 * falling_t)

        return config.BREATH_FLOOR + (1.0 - config.BREATH_FLOOR) * pulse

    return alpha


def render_clip(
    fig: Figure,
    ax: Axes3D,
    view: GraphView,
    path: Path,
    frames: int,
    pos_for: Callable[[int], NDArray[np.float64]],
    camera_for: Callable[[int], Camera],
    alpha_for: Callable[[int], NDArray[np.float64]] | None = None,
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
        camera_for: Maps a frame index to an (elev, azim, roll) tuple.
        alpha_for: Optional map from frame index to per-node alpha multipliers.
    """

    def animate(frame: int) -> list[Artist]:
        elev, azim, roll = camera_for(frame)
        view.pos = pos_for(frame)
        if alpha_for is not None:
            view.set_alpha_scale(alpha_for(frame))
        ax.view_init(elev=elev, azim=azim, roll=roll)
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
    camera: Camera,
    path: Path,
    alpha_scale: NDArray[np.float64] | None = None,
) -> None:
    """Save a WebP poster matching frame 0 of the loop.

    The PNG is written at figure DPI and downscaled with Pillow rather than
    saved at a lower DPI directly, because the label collection bakes in
    fig.dpi/72 at construction time and would not rescale with savefig.

    Args:
        fig: The figure to capture.
        ax: The 3D axes to orient.
        view: The GraphView to position.
        positions: The (N, 3) node positions at frame 0, drift included.
        camera: The (elev, azim, roll) tuple at frame 0.
        path: Output .webp path.
        alpha_scale: Optional per-node alpha multipliers for the poster.
    """
    elev, azim, roll = camera
    view.pos = positions
    if alpha_scale is not None:
        view.set_alpha_scale(alpha_scale)
    ax.view_init(elev=elev, azim=azim, roll=roll)

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
    drift = drift_field(view.graph.number_of_nodes())
    breath = breath_field(view.graph.number_of_nodes())

    if config.RENDER_INTRO:
        history = tween_history(spawn_positions, final_positions, config.INTRO_FRAMES)
        render_clip(
            fig,
            ax,
            view,
            config.STATIC_DIR / "hero-intro.mp4",
            config.INTRO_FRAMES,
            pos_for=lambda frame: history[min(frame, len(history) - 1)],
            camera_for=intro_camera,
        )

    render_clip(
        fig,
        ax,
        view,
        config.STATIC_DIR / "hero-loop.mp4",
        config.LOOP_FRAMES,
        pos_for=lambda frame: final_positions + drift(frame),
        camera_for=loop_camera,
        alpha_for=breath,
    )

    save_poster(
        fig,
        ax,
        view,
        final_positions + drift(0),
        loop_camera(0),
        config.STATIC_DIR / "hero-poster.webp",
        alpha_scale=breath(0),
    )
    plt.close(fig)


if __name__ == "__main__":
    main()
