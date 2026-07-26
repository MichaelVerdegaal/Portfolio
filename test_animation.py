from collections.abc import Iterable

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import numpy.typing as npt
from fa2 import ForceAtlas2
from matplotlib.animation import FuncAnimation

from src.animate import tween_history
from src.graphview import GraphView, load_graph_data
from src.mpl_utils import create_figure

TARGET_FPS = 60
DURATION_SECONDS = 10
INTERVAL_MS = 1000 // TARGET_FPS
FRAMES = int(DURATION_SECONDS * TARGET_FPS)
AXIS_MIN = 0
AXIS_MAX = 100
IS_3D = True


# --- Layout ---------------------------------------------------------------------------
def rescale_uniform(coords: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Rescale a set of 2D/3D coordinates to fit within [lo, hi] uniformly.

    Args:
        coords: An (N, 2) or (N, 3) array of coordinates.
        lo: The lower bound of the target range.
        hi: The upper bound of the target range.

    Returns:
        An (N, 2) or (N, 3) array of rescaled coordinates within [lo, hi].
    """
    mins = coords.min(axis=0)
    maxs = coords.max(axis=0)
    scale = (hi - lo) / max(np.ptp(coords, axis=0).max(), 1e-12)
    centered = coords - (mins + maxs) / 2.0
    return centered * scale + (lo + hi) / 2.0


def layout_function(graph_view: GraphView, is_3d: bool) -> npt.NDArray[np.float64]:
    """Compute a target layout for the graph using ForceAtlas2.

    Args:
        graph_view: The GraphView instance containing the graph and its current positions.

    Returns:
        An (N, 2) | (N, 3) array of target positions for the graph nodes.
    """
    pos = graph_view.pos.copy()
    G_sparse = nx.to_scipy_sparse_array(graph_view.graph.to_undirected())

    fa2: ForceAtlas2 = ForceAtlas2.inferSettings(
        G_sparse, seed=3, verbose=False, backend="vectorized", dim=3 if is_3d else None
    )
    layout = fa2.forceatlas2(G_sparse, pos=pos, iterations=100)

    layout_np = np.array(layout)
    return rescale_uniform(layout_np, AXIS_MIN + 10.0, AXIS_MAX - 10.0)


# --- Initialize graph -----------------------------------------------------------------

fig, ax = create_figure(is_3d=IS_3D)
graph_data: dict[str, Iterable[str]] = load_graph_data()
G = GraphView(
    fig,
    ax,
    nx.DiGraph(graph_data),
    axis_lim=(AXIS_MIN, AXIS_MAX),
    spawn_margin=20,
    is_3d=IS_3D,
)

# --- Main  ----------------------------------------------------------------------------
start = G.pos.copy()
final_layout = layout_function(G, IS_3D)
history = tween_history(start, final_layout, FRAMES)


def animate(frame: int):
    """Show the recorded ForceAtlas2 layout at the given iteration.

    Args:
        frame: The current frame index into the position history.

    Returns:
        The node and edge artists for blitting.
    """
    G.pos = history[min(frame, len(history) - 1)]

    return G.get_artists()


# Blitting has limited support with Axes3D
enable_blitting: bool = False if IS_3D else True
anim = FuncAnimation(
    fig,
    func=animate,
    interval=INTERVAL_MS,
    frames=FRAMES,
    repeat=False,
    blit=enable_blitting,
)
# save animation as mp4
# anim.save("animation.mp4", writer="ffmpeg")

plt.tight_layout()
plt.show()
