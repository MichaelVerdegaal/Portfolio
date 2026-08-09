from collections.abc import Callable

import numpy as np


def ease_smoothstep(t: float) -> float:
    """Smoothstep easing function for smooth transition.

    Args:
        t: A float in [0, 1] representing normalised time.

    Returns:
        The eased value, also in [0, 1].
    """
    return t * t * (3 - 2 * t)


def step_history(
    start: np.ndarray,
    step_fn: Callable[[np.ndarray], np.ndarray],
    frames: int,
) -> np.ndarray:
    """Iteratively apply a step function to generate a position history.

    step_fn returns a displacement that is added to the current position
    each frame.

    Args:
        start: Initial (N, 2|3) position array.
        step_fn: Function that takes the current (N, 2|3) positions and
            returns a (N, 2|3) displacement.
        frames: Number of frames in the output history.

    Returns:
        An array of shape (frames, N, 2|3) with the position at each frame.
    """
    history = np.empty((frames, *start.shape))
    pos = start.copy()
    for i in range(frames):
        history[i] = pos
        pos = pos + step_fn(pos)
    return history


def tween_history(
    start: np.ndarray,
    target: np.ndarray,
    frames: int,
    ease: Callable[[float], float] = ease_smoothstep,
) -> np.ndarray:
    """Interpolate from start to a precomputed target layout.

    Uses an easing function to generate smooth transitions. This is a
    one-shot computation, not iterative.

    Args:
        start: Initial (N, 2|3) position array.
        target: Target (N, 2|3) position array.
        frames: Number of frames in the output history.
        ease: Easing function mapping [0, 1] -> [0, 1]. Defaults to
            ease_smoothstep.

    Returns:
        An array of shape (frames, N, 2|3 with the interpolated position
        at each frame.
    """
    t = np.array([ease(i / (frames - 1)) for i in range(frames)])
    return start + (target - start) * t[:, None, None]
