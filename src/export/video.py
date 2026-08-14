"""FFmpeg video rendering for matplotlib animations."""

import shutil
from collections.abc import Callable
from pathlib import Path

from matplotlib.animation import FFMpegWriter, FuncAnimation
from matplotlib.figure import Figure

from ..config import CRF, DPI, FPS, PRESET, VIDEO_FILTERS


def check_ffmpeg() -> None:
    """Raise FileNotFoundError if ffmpeg is not on PATH."""
    if shutil.which("ffmpeg") is None:
        raise FileNotFoundError("ffmpeg is not on PATH; install ffmpeg to export video")


def render_clip(
    fig: Figure,
    update: Callable[[int], object],
    path: Path,
    frames: int,
) -> None:
    """Render a clip to MP4 in a single ffmpeg pass.

    Frames are piped to ffmpeg at FIGSIZE * DPI and downscaled to the target
    resolution by the scale filter in the writer's extra_args, so there is no
    second encode.

    Args:
        fig: The figure to capture.
        update: FuncAnimation callback that advances the scene for a frame.
        path: Output file path.
        frames: Number of frames to render.
    """
    writer = FFMpegWriter(
        fps=FPS,
        codec="libx264",
        extra_args=[
            "-vf",
            VIDEO_FILTERS,
            "-crf",
            str(CRF),
            "-preset",
            PRESET,
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
        update,
        frames=frames,
        interval=1000 // FPS,
        repeat=False,
        blit=False,
        cache_frame_data=False,
    )
    anim.save(str(path), writer=writer, dpi=DPI)
