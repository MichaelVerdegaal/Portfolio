from collections.abc import Callable

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

from src.graph import Graph, Node, load_graph_data
from src.mpl_utils import create_figure

# Config animation
TARGET_FPS = 60
DURATION_SECONDS: int = 5  # Animation duration in seconds
INTERVAL_MS: int = 1000 // TARGET_FPS  # Animation interval in milliseconds
FRAMES = int(DURATION_SECONDS * TARGET_FPS)  # Total number of frames in the animation
SAVE_PATH: str | None = "animation.mp4"  # e.g. "animation.gif", None = show only
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


# --- Main ----------------------------------------------------------------------
fig, ax = create_figure()
G: Graph = Graph(fig=fig, ax=ax, graph=graph_dict)


# --- Layout --------------------------------------------------------------------
def layout_children(parent_name: str, visited: set[str]) -> None:
    """Recursively move children that are above their parent to parent_y - 5."""
    if parent_name in visited:
        return
    visited.add(parent_name)

    parent_coords = G.get_node_coords(parent_name)
    if parent_coords is None:
        return

    parent_y = float(parent_coords[1])
    for child in G.get_children(parent_name):
        child_coords = G.get_node_coords(child)
        if child_coords is None:
            continue
        G.move_node(child, np.array([child_coords[0], parent_y - 10]))
        layout_children(child, visited)


root_node: Node | None = G.move_node("A", np.array([50, 75]))
if root_node is not None:
    layout_children("A", set())

# --- Animate --------------------------------------------------------------------
start_layout = G._coords_original
final_layout = G._coords.copy()
history = tween_history(start_layout, final_layout, FRAMES)


def animate(frame: int):
    # coords = GScene.coords

    # transform
    new_coords = history[frame]

    # update scene
    G.coords = new_coords

    return G.get_artists()


anim = FuncAnimation(
    fig, func=animate, interval=INTERVAL_MS, frames=FRAMES, repeat=False
)
if SAVE_PATH:
    anim.save(SAVE_PATH, writer="ffmpeg", fps=TARGET_FPS)
plt.show()
