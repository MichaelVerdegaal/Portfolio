from collections.abc import Callable

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from matplotlib.animation import FuncAnimation

from src.graph import Graph, GraphScene, load_graph_data
from src.mpl_utils import create_figure

# Config animation
TARGET_FPS = 60
DURATION_SECONDS: int = 5  # Animation duration in seconds
INTERVAL_MS: int = 1000 // TARGET_FPS  # Animation interval in milliseconds
FRAMES = int(DURATION_SECONDS * TARGET_FPS)  # Total number of frames in the animation
SAVE_PATH: str | None = "animation.gif"  # e.g. "animation.gif", None = show only
print(f"{TARGET_FPS=}, {DURATION_SECONDS=}, {INTERVAL_MS=}, {FRAMES=}")

# Load data from YAML
graph_dict: dict[str, list[str]] = load_graph_data()


# --- History builders: every mode ends as a (frames, N, 2) array ---------------
def ease_bezier(t: float) -> float:
    """Cubic bezier easing function for smooth transition"""
    return t * t * (3 - 2 * t)


def tween_history(
    start: np.ndarray,
    target: np.ndarray,
    frames: int,
    ease: Callable[[float], float] = ease_bezier,
) -> np.ndarray:
    """One-shot: interpolate from start to a precomputed target layout."""
    t = np.array([ease(i / (frames - 1)) for i in range(frames)])
    return start + (target - start) * t[:, None, None]


def step_history(
    start: np.ndarray,
    step_fn: Callable[[np.ndarray], np.ndarray],
    frames: int,
) -> np.ndarray:
    """Iterative: step_fn returns a displacement, applied cumulatively."""
    history = np.empty((frames, *start.shape))
    pos = start.copy()
    for i in range(frames):
        history[i] = pos
        pos = pos + step_fn(pos)
    return history


# --- Layout --------------------------------------------------------------------


# --- Main ----------------------------------------------------------------------
fig, ax = create_figure()
G: Graph = Graph(graph_dict)
GScene: GraphScene = GraphScene(G, fig, ax)

target_len: np.float64 = GScene.edge_lengths.mean()
final_layout: npt.NDArray[np.float64] = np.random.uniform(
    low=0, high=80, size=(len(GScene.graph.node_names), 2)
)
history = tween_history(GScene.coords, final_layout, FRAMES)


def animate(frame: int):
    # coords = GScene.coords

    # transform
    new_coords = history[frame]

    # update scene
    GScene.coords = new_coords
    return GScene._scatter, GScene._edge_lines


anim = FuncAnimation(
    fig, func=animate, interval=INTERVAL_MS, frames=FRAMES, repeat=True
)
fig.tight_layout()
if SAVE_PATH:
    anim.save(SAVE_PATH, writer="pillow", fps=TARGET_FPS)
plt.show()
