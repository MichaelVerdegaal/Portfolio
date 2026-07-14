from collections.abc import Callable, Iterable

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.animation import FuncAnimation

from src.graph import GraphView, load_graph_data
from src.mpl_utils import create_figure

TARGET_FPS = 60
DURATION_SECONDS = 5
INTERVAL_MS = 1000 // TARGET_FPS
FRAMES = int(DURATION_SECONDS * TARGET_FPS)


# --- History builders: every mode ends as a (frames, N, 2) array ----------------------
def ease_bezier(t: float) -> float:
    """Cubic bezier easing function for smooth transition"""
    return t * t * (3 - 2 * t)


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


def tween_history(
    start: np.ndarray,
    target: np.ndarray,
    frames: int,
    ease: Callable[[float], float] = ease_bezier,
) -> np.ndarray:
    """One-shot: interpolate from start to a precomputed target layout."""
    t = np.array([ease(i / (frames - 1)) for i in range(frames)])
    return start + (target - start) * t[:, None, None]


# --- Layout ---------------------------------------------------------------------------
def layout_by_depth(
    view: GraphView, root: int, top: float = 75.0, dy: float = 10.0
) -> None:
    """Set each node's y from its BFS depth below root; x is left untouched."""
    for depth, layer in enumerate(nx.bfs_layers(view.graph, root)):
        view._pos[list(layer), 1] = top - depth * dy
    view.refresh()


# --- Initialize graph -----------------------------------------------------------------
fig, ax = create_figure()
graph_data: dict[str, Iterable[str]] = load_graph_data()
G = GraphView(fig, ax, nx.DiGraph(graph_data), axis_lim=(0, 100), spawn_margin=20)
start_layout = G.pos.copy()

# --- Main  ----------------------------------------------------------------------------

# root is A, which relabels to node 0; find it structurally to be safe
root_node = next(n for n in G.graph if G.graph.in_degree(n) == 0)
G.move_node(root_node, (50, 75))  # place root at top center
layout_by_depth(G, root_node)

final_layout = G.pos.copy()
history = tween_history(start_layout, final_layout, FRAMES)


def animate(frame: int):
    """Main animation function for FuncAnimation; called once per frame."""
    G.pos = history[frame]  # setter calls refresh()

    return G.get_artists()


anim = FuncAnimation(
    fig, func=animate, interval=INTERVAL_MS, frames=FRAMES, repeat=True
)
plt.show()
