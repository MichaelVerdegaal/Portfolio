from collections.abc import Callable, Iterable
from matplotlib.text import Annotation, Text
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.animation import FuncAnimation

from src.graph import GraphView, load_graph_data
from src.mpl_utils import create_figure, COLOR_EDGES

TARGET_FPS = 60
DURATION_SECONDS = 5
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
def reorder(
    view: GraphView,
    root: int,
    layers: list[list[int]],
    dx: float = 10,
    iterations: int = 2,
) -> GraphView:
    """Refine node ordering across layers to reduce edge crossings.

    Alternates top-down and bottom-up barycenter sweeps per iteration,
    a simplified Sugiyama crossing reduction.

    Args:
        view: The GraphView whose nodes will be reordered.
        root: The integer id of the root node.
        layers: A list of layers, each a list of node IDs.
        dx: Horizontal spacing between nodes within the same layer.
        iterations: Number of top-down/bottom-up sweep pairs.

    Returns:
        The GraphView with nodes reordered.
    """
    for _ in range(iterations):
        # --- Top-down: order each layer by mean x of its parents ---
        for layer in layers[1:]:
            barycenter = {}
            for node in layer:
                parents = list(view.graph.predecessors(node))
                barycenter[node] = (
                    np.mean([view.get_node_coords(p)[0] for p in parents])
                    if parents
                    else view.get_node_coords(node)[0]
                )
            order = [n for n, _ in sorted(barycenter.items(), key=lambda kv: kv[1])]
            center_x = view.get_node_coords(root)[0]
            for i, node in enumerate(order):
                view._pos[node, 0] = center_x + (i - (len(order) - 1) / 2) * dx

        # --- Bottom-up: order each layer by mean x of its children ---
        for layer in reversed(layers[:-1]):
            barycenter = {}
            for node in layer:
                children = list(view.graph.successors(node))
                barycenter[node] = (
                    np.mean([view.get_node_coords(c)[0] for c in children])
                    if children
                    else view.get_node_coords(node)[0]
                )
            order = [n for n, _ in sorted(barycenter.items(), key=lambda kv: kv[1])]
            center_x = view.get_node_coords(root)[0]
            for i, node in enumerate(order):
                view._pos[node, 0] = center_x + (i - (len(order) - 1) / 2) * dx

    return view


def layout_func(
    view: GraphView, root: int, top: float = 75, dy: float = 10, dx: float = 3
) -> None:
    """Arrange nodes vertically by BFS depth below the root.

    Each BFS layer is placed at a fixed y coordinate. Node x coordinates
    are left unchanged.

    Args:
        view: The GraphView whose nodes will be repositioned.
        root: The integer id of the root node.
        top: The y coordinate of the root layer.
        dy: Vertical spacing between successive layers.
        dx: Horizontal spacing between nodes within the same layer.
    """

    # Re-usable list of layers, each a list of node ID's
    layers = [list(layer) for layer in nx.bfs_layers(view.graph, root)]

    # First we fix the height so that no child is above their parent.
    for depth, layer in enumerate(layers):
        view._pos[layer, 1] = top - depth * dy

    # Root keeps its order; each deeper layer is ordered by the mean x of its
    # parents in the already-fixed layer above.
    new_view = reorder(view, root, layers, dx=dx, iterations=10)

    new_view.refresh()


# --- Initialize graph -----------------------------------------------------------------
fig, ax = create_figure()
graph_data: dict[str, Iterable[str]] = load_graph_data()
G = GraphView(fig, ax, nx.DiGraph(graph_data), axis_lim=(0, 100), spawn_margin=20)
start_layout = G.pos.copy()

# --- Main  ----------------------------------------------------------------------------
coords_root: tuple[float, float] = (50, 75)
root_node = [n for n in G.graph if G.graph.in_degree(n) == 0][0]
G.move_node(root_node, coords_root)  # place root at top center
layout_func(G, root_node)

final_layout = G.pos.copy()
history = tween_history(start_layout, final_layout, FRAMES)


def animate(frame: int):
    """Update node positions for a single animation frame.

    Args:
        frame: The current frame index.

    Returns:
        The node and edge artists for blitting.
    """
    G.pos = history[frame]  # setter calls refresh()

    return G.get_artists()


anim = FuncAnimation(
    fig, func=animate, interval=INTERVAL_MS, frames=FRAMES, repeat=False
)
plt.tight_layout()
plt.show()
