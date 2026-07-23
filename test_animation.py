from collections.abc import Iterable

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import numpy.typing as npt
from fa2 import ForceAtlas2
from matplotlib.animation import FuncAnimation

from src.graph import GraphView, load_graph_data
from src.mpl_utils import create_figure

TARGET_FPS = 60
DURATION_SECONDS = 10
INTERVAL_MS = 1000 // TARGET_FPS
FRAMES = int(DURATION_SECONDS * TARGET_FPS)
AXIS_MIN = 0
AXIS_MAX = 100


# --- Debugging ------------------------------------------------------------------------


def count_crossings(above: list[int], below: list[int], graph: nx.DiGraph) -> int:
    """Count edge crossings between two adjacent layers.

    Two edges (u1, v1) and (u2, v2) cross when their endpoints are in
    opposite order in the two layers.

    Args:
        above: Node ids of the upper layer, in left-to-right order.
        below: Node ids of the lower layer, in left-to-right order.
        graph: The directed graph containing the edges.

    Returns:
        The number of crossing edge pairs between the two layers.
    """
    ix_above = {n: i for i, n in enumerate(above)}
    ix_below = {n: i for i, n in enumerate(below)}
    edges = [
        (ix_above[u], ix_below[v])
        for u in above
        for v in graph.successors(u)
        if v in ix_below
    ]
    return sum(
        1
        for i, (u1, v1) in enumerate(edges)
        for u2, v2 in edges[i + 1 :]
        if (u1 - u2) * (v1 - v2) < 0
    )


def total_crossings(layers: list[list[int]], graph: nx.DiGraph) -> int:
    """Sum edge crossings over all adjacent layer pairs.

    Args:
        layers: Layer orderings, top to bottom.
        graph: The directed graph containing the edges.

    Returns:
        The total crossing count for the whole layout.
    """
    return sum(
        count_crossings(layers[i], layers[i + 1], graph) for i in range(len(layers) - 1)
    )


# --- Layout ---------------------------------------------------------------------------
def forceatlas2_history(
    graph: nx.DiGraph,
    start: npt.NDArray[np.float64],
    iterations: int,
) -> npt.NDArray[np.float64]:
    """Run ForceAtlas2 and record node positions at every iteration.

    The directed graph is symmetrised to the undirected adjacency matrix
    ForceAtlas2 expects; layout runs to completion up front and the
    animation replays the recorded history.

    Args:
        graph: The directed graph with integer nodes 0..N-1.
        start: Initial (N, 2) position array. Not modified.
        iterations: Number of ForceAtlas2 iterations to run.

    Returns:
        An array of shape (iterations, N, 2) with the position at each
        iteration.
    """
    adjacency = nx.to_scipy_sparse_array(
        graph.to_undirected(), nodelist=sorted(graph), dtype=np.float64
    )
    snapshots: list[npt.NDArray[np.float64]] = []

    def record(iteration: int, nodes: list) -> None:
        snapshots.append(np.array([[n.x, n.y] for n in nodes]))

    engine = ForceAtlas2(
        outboundAttractionDistribution=True,  # dissuade hubs
        scalingRatio=2.0,
        gravity=1.0,
        jitterTolerance=1.0,
        seed=3,
        verbose=False,
        backend="vectorized",
    )
    engine.forceatlas2(
        adjacency, pos=start.copy(), iterations=iterations, callbacks=[record]
    )
    return np.array(snapshots)


def fit_to_canvas(
    history: npt.NDArray[np.float64],
    low: float = AXIS_MIN + 10.0,
    high: float = AXIS_MAX - 10.0,
) -> npt.NDArray[np.float64]:
    """Rescale a position history into fixed axis bounds.

    ForceAtlas2 layouts live on an arbitrary scale, so each frame is
    uniformly scaled (aspect preserved) and centered to fit the canvas.

    Args:
        history: (frames, N, 2) position array.
        low: Lower axis bound the layout should fit inside.
        high: Upper axis bound the layout should fit inside.

    Returns:
        A rescaled (frames, N, 2) array within [low, high].
    """
    mins = history.min(axis=1, keepdims=True)  # (frames, 1, 2)
    maxs = history.max(axis=1, keepdims=True)
    span = np.maximum((maxs - mins).max(axis=2, keepdims=True), 1e-9)  # (frames, 1, 1)
    scale = (high - low) / span
    center = (mins + maxs) / 2
    return (history - center) * scale + (low + high) / 2


# --- Initialize graph -----------------------------------------------------------------
fig, ax = create_figure()
graph_data: dict[str, Iterable[str]] = load_graph_data()
G = GraphView(fig, ax, nx.DiGraph(graph_data), axis_lim=(AXIS_MIN, AXIS_MAX), spawn_margin=20)

# --- Main  ----------------------------------------------------------------------------
history = fit_to_canvas(forceatlas2_history(G.graph, G.pos, FRAMES))


def animate(frame: int):
    """Show the recorded ForceAtlas2 layout at the given iteration.

    Args:
        frame: The current frame index into the position history.

    Returns:
        The node and edge artists for blitting.
    """
    G.pos = history[min(frame, len(history) - 1)]

    return G.get_artists()


anim = FuncAnimation(
    fig, func=animate, interval=INTERVAL_MS, frames=FRAMES, repeat=False, blit=True
)
# save animation as mp4
# anim.save("animation.mp4", writer="ffmpeg")

plt.tight_layout()
plt.show()
