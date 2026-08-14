"""Camera orientation factories for the looping and intro clips."""

import math
from collections.abc import Callable

from ..config import (
    AZIM0,
    AZIM_AMPLITUDE,
    DEG_PER_FRAME,
    ELEV0,
    ELEV_AMPLITUDE,
    ELEV_AMPLITUDE_3,
    ELEV_PHASE,
    INTRO_FRAMES,
    LOOP_FRAMES,
    PREVIEW_AZIM_ROTATIONS,
    PREVIEW_ELEV_ROTATIONS,
    ROLL_AMPLITUDE,
    ROLL_PHASE,
)

Camera = tuple[float, float, float]


def loop_azim(frame: int) -> float:
    """Azimuth oscillating around AZIM0, one cycle per loop.

    Args:
        frame: Frame index within the loop clip.

    Returns:
        The camera azimuth in degrees.
    """
    t = frame / LOOP_FRAMES
    return AZIM0 + AZIM_AMPLITUDE * math.sin(2 * math.pi * t)


def loop_elev(frame: int) -> float:
    """Elevation built from a first and third harmonic.

    The third harmonic and the phase offset keep the vertical motion from
    reading as a metronome synchronised with the azimuth sweep.

    Args:
        frame: Frame index within the loop clip.

    Returns:
        The camera elevation in degrees.
    """
    t = frame / LOOP_FRAMES
    return (
        ELEV0
        + ELEV_AMPLITUDE * math.sin(2 * math.pi * t + ELEV_PHASE)
        + ELEV_AMPLITUDE_3 * math.sin(2 * math.pi * 3 * t)
    )


def loop_roll(frame: int) -> float:
    """Camera roll on a second harmonic.

    Args:
        frame: Frame index within the loop clip.

    Returns:
        The camera roll in degrees.
    """
    t = frame / LOOP_FRAMES
    return ROLL_AMPLITUDE * math.sin(2 * math.pi * 2 * t + ROLL_PHASE)


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
    return (AZIM0 - DEG_PER_FRAME * (INTRO_FRAMES - frame)) % 360


def intro_camera(frame: int) -> Camera:
    """Camera orientation for the intro clip.

    Unused while config.RENDER_INTRO is False. Kept for the project page.

    Args:
        frame: Frame index within the intro clip.

    Returns:
        An (elev, azim, roll) tuple in degrees.
    """
    return (ELEV0, intro_azim(frame), 0.0)


def spin_camera(
    frames: int,
    elev_rotations: float = PREVIEW_ELEV_ROTATIONS,
    azim_rotations: float = PREVIEW_AZIM_ROTATIONS,
) -> Callable[[int], Camera]:
    """Linear camera spin for the interactive preview.

    Args:
        frames: Number of frames in the preview animation.
        elev_rotations: Number of full elevation rotations over the clip.
        azim_rotations: Number of full azimuth rotations over the clip.

    Returns:
        A factory mapping a frame index to an (elev, azim, roll) tuple.
    """

    def camera(frame: int) -> Camera:
        progress = frame / max(frames - 1, 1)
        return (
            ELEV0 + 360 * elev_rotations * progress,
            AZIM0 + 360 * azim_rotations * progress,
            0.0,
        )

    return camera
