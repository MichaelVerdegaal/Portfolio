from collections.abc import Callable, Iterable
from itertools import combinations

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.animation import FuncAnimation
from networkx.classes.reportviews import NodeView
from numpy import float64
from numpy._typing._array_like import NDArray

from src.graph import GraphView, load_graph_data
from src.mpl_utils import create_figure

TARGET_FPS = 60
DURATION_SECONDS = 10
INTERVAL_MS = 1000 // TARGET_FPS
FRAMES = int(DURATION_SECONDS * TARGET_FPS)


# --- History builders: every mode ends as a (frames, N, 2) array ----------------------
def ease_bezier(t: float) -> float:
    """Cubic bezier easing function for smooth transition.

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
        start: Initial (N, 2) position array.
        step_fn: Function that takes the current (N, 2) positions and
            returns a (N, 2) displacement.
        frames: Number of frames in the output history.

    Returns:
        An array of shape (frames, N, 2) with the position at each frame.
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
    ease: Callable[[float], float] = ease_bezier,
) -> np.ndarray:
    """Interpolate from start to a precomputed target layout.

    Uses an easing function to generate smooth transitions. This is a
    one-shot computation, not iterative.

    Args:
        start: Initial (N, 2) position array.
        target: Target (N, 2) position array.
        frames: Number of frames in the output history.
        ease: Easing function mapping [0, 1] -> [0, 1]. Defaults to
            ease_bezier.

    Returns:
        An array of shape (frames, N, 2) with the interpolated position
        at each frame.
    """
    t = np.array([ease(i / (frames - 1)) for i in range(frames)])
    return start + (target - start) * t[:, None, None]


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
def fr_step(
    iteration: int,
    view: GraphView,
    node_pairs: list[tuple[int, int]],
    edges: list[tuple[int, int]],
    k: float,
    t_initial: float,
) -> None:
    """Run a single Fruchterman-Reingold iteration in place.

    Args:
        iteration: The current iteration number
        view: The GraphView whose nodes will be moved.
        node_pairs: All ordered node pairs, for the repulsion sweep.
        edges: The graph edges, for the attraction sweep.
        k: Ideal edge length constant.
        t_initial: Maximum displacement per iteration (initial temperature).
    """
    t = t_initial * (1 - iteration / FRAMES)

    nodes: NodeView = view.graph.nodes
    disp = {}

    # Reset displacement
    for n in nodes:
        disp[n] = 0

    # Calculate repulsion for all node pairs
    for n1, n2 in node_pairs:
        pos_n1 = view._pos[n1]
        pos_n2 = view._pos[n2]
        delta: NDArray[float64] = pos_n1 - pos_n2
        d = max(np.linalg.norm(delta), 0.01)
        disp[n1] += (delta / d) * (k**2 / d)
        disp[n2] -= (delta / d) * (k**2 / d)

    # Calculate attraction for all edges
    for n1, n2 in edges:
        pos_n1 = view._pos[n1]
        pos_n2 = view._pos[n2]
        delta: NDArray[float64] = pos_n1 - pos_n2
        d = max(np.linalg.norm(delta), 0.01)
        disp[n1] -= (delta / d) * (d**2 / k)
        disp[n2] += (delta / d) * (d**2 / k)

    # Set new positions based on displacement, limited to t units per iteration
    for n in nodes:
        pos_n = view._pos[n]
        length = np.linalg.norm(disp[n])
        if length > 0.0:
            view._pos[n] = pos_n + disp[n] / length * min(length, t)

    view._pos = np.clip(view._pos, 0, 100, out=view._pos)

    view.refresh()


def layout_func(view: GraphView, root: int, top: float = 75, dy: float = 10) -> None:
    """Arrange nodes vertically by BFS depth below the root.

    Sets the starting positions the live layout begins from. The
    Fruchterman-Reingold iterations then run one per animation frame.

    Args:
        view: The GraphView whose nodes will be repositioned.
        root: The integer id of the root node.
        top: The y coordinate of the root layer.
        dy: Vertical spacing between successive layers.
    """

    # Re-usable list of layers, each a list of node ID's
    layers = [list(layer) for layer in nx.bfs_layers(view.graph, root)]

    # Fix the height so that no child is above their parent.
    for depth, layer in enumerate(layers):
        view._pos[layer, 1] = top - depth * dy

    view.refresh()


# --- Initialize graph -----------------------------------------------------------------
fig, ax = create_figure()
graph_data: dict[str, Iterable[str]] = load_graph_data()
G = GraphView(fig, ax, nx.DiGraph(graph_data), axis_lim=(0, 100), spawn_margin=20)

# --- Main  ----------------------------------------------------------------------------
# coords_root: tuple[float, float] = (50, 75)
# root_node = [n for n in G.graph if G.graph.in_degree(n) == 0][0]
# G.move_node(root_node, coords_root)  # place root at top center
# layout_func(G, root_node)  # initial BFS layering; FR runs live per frame

# Fixed topology + FR knobs, computed once
nodes = G.graph.nodes
node_pairs = list(combinations(nodes, 2))
edges = list(G.graph.edges)
area: int = 100
C: float = 0.6
k: float = 4
t: float = 0.1


def animate(frame: int):
    """Advance the layout by one Fruchterman-Reingold iteration.

    Args:
        frame: The current frame index (unused; each call is one FR step).

    Returns:
        The node and edge artists for blitting.
    """
    fr_step(frame, G, node_pairs, edges, k, t)

    return G.get_artists()


anim = FuncAnimation(
    fig, func=animate, interval=INTERVAL_MS, frames=FRAMES, repeat=False, blit=True
)
# save animation as mp4
anim.save("animation.mp4", writer="ffmpeg")

plt.tight_layout()
plt.show()
