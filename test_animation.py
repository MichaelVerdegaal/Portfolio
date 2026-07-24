from collections.abc import Iterable

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import numpy.typing as npt
from fa2 import ForceAtlas2
from matplotlib.animation import FuncAnimation

from src.animate import tween_history
from src.graphview import GraphView, load_graph_data
from src.mpl_utils import create_figure_3d

TARGET_FPS = 60
DURATION_SECONDS = 10
INTERVAL_MS = 1000 // TARGET_FPS
FRAMES = int(DURATION_SECONDS * TARGET_FPS)
AXIS_MIN = 0
AXIS_MAX = 100
CAMERA_ELEV = 18
CAMERA_AZIM = -60
# Half a turn over the whole animation.
SPIN_DEG_PER_FRAME = 180 / FRAMES


# --- Layout ---------------------------------------------------------------------------
def fit_to_canvas(
    history: npt.NDArray[np.float64],
    low: float = AXIS_MIN + 10.0,
    high: float = AXIS_MAX - 10.0,
) -> npt.NDArray[np.float64]:
    """Rescale a position history into fixed axis bounds.

    ForceAtlas2 layouts live on an arbitrary scale, so each frame is
    uniformly scaled (aspect preserved) and centered to fit the canvas.

    Args:
        history: (frames, N, 3) position array.
        low: Lower axis bound the layout should fit inside.
        high: Upper axis bound the layout should fit inside.

    Returns:
        A rescaled (frames, N, 3) array within [low, high].
    """
    mins = history.min(axis=1, keepdims=True)  # (frames, 1, 3)
    maxs = history.max(axis=1, keepdims=True)
    span = np.maximum((maxs - mins).max(axis=2, keepdims=True), 1e-9)  # (frames, 1, 1)
    scale = (high - low) / span
    center = (mins + maxs) / 2
    return (history - center) * scale + (low + high) / 2


# --- Initialize graph -----------------------------------------------------------------
fig, ax = create_figure_3d()
graph_data: dict[str, Iterable[str]] = load_graph_data()
G = GraphView(
    fig, ax, nx.DiGraph(graph_data), axis_lim=(AXIS_MIN, AXIS_MAX), spawn_margin=20
)

# --- Main  ----------------------------------------------------------------------------
start = G.pos.copy()
undirected = G.graph.to_undirected()

fa2 = ForceAtlas2.inferSettings(
    undirected,
    dim=3,
    seed=3,
    verbose=False,
    backend="vectorized",
)
layout = fa2.forceatlas2_networkx_layout(
    undirected,
    pos={n: start[n] for n in undirected},
    iterations=100,
)
target = fit_to_canvas(np.array([layout[n] for n in G.graph])[np.newaxis, ...])[0]
history = tween_history(start, target, FRAMES)


def animate(frame: int):
    """Show the recorded ForceAtlas2 layout at the given iteration.

    Args:
        frame: The current frame index into the position history.

    Returns:
        The node, edge, and label artists.
    """
    # Camera first: refresh() projects label offsets through the current
    # view matrix, so moving the camera after would lag them one frame.
    ax.view_init(elev=CAMERA_ELEV, azim=CAMERA_AZIM + frame * SPIN_DEG_PER_FRAME)
    G.pos = history[min(frame, len(history) - 1)]

    return G.get_artists()


# blit can't work on a 3D axes: the projection happens in Axes3D.draw, and
# the spinning camera invalidates the whole scene every frame anyway.
anim = FuncAnimation(
    fig, func=animate, interval=INTERVAL_MS, frames=FRAMES, repeat=False, blit=False
)
# save animation as mp4
# anim.save("animation.mp4", writer="ffmpeg")

plt.tight_layout()
plt.show()
