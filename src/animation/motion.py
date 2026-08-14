"""Per-node positional drift and opacity breathing fields."""

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from ..config import (
    BREATH_DUTY,
    BREATH_FLOOR,
    BREATH_HARMONICS,
    BREATH_SEED,
    DRIFT_AMPLITUDES,
    DRIFT_HARMONICS,
    DRIFT_SEED,
    LOOP_FRAMES,
)


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
    rng = np.random.default_rng(DRIFT_SEED)
    harmonics = np.array(DRIFT_HARMONICS, dtype=np.float64)[:, None, None]
    shape = (len(DRIFT_HARMONICS), node_count, 3)
    phases = rng.uniform(0.0, 1.0, shape)
    scales = rng.uniform(0.4, 1.0, shape)
    amplitudes = np.array(DRIFT_AMPLITUDES)[:, None, None] * scales

    def offset(frame: int) -> NDArray[np.float64]:
        t = frame / LOOP_FRAMES
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
    rng = np.random.default_rng(BREATH_SEED)
    harmonics = rng.choice(BREATH_HARMONICS, size=node_count).astype(float)
    phases = rng.uniform(0.0, 1.0, node_count)
    ramp = 0.5 * BREATH_DUTY

    def alpha(frame: int) -> NDArray[np.float64]:
        t = frame / LOOP_FRAMES
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

        return BREATH_FLOOR + (1.0 - BREATH_FLOOR) * pulse

    return alpha
