from collections.abc import Callable, Iterable

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import numpy.typing as npt
from matplotlib.animation import FuncAnimation

from src.graph import GraphView, load_graph_data
from src.mpl_utils import create_figure

TARGET_FPS = 60
DURATION_SECONDS = 10
INTERVAL_MS = 1000 // TARGET_FPS
FRAMES = int(DURATION_SECONDS * TARGET_FPS)


# --- History builders: every mode ends as a (frames, N, 2) array ----------------------
def ease_smoothstep(t: float) -> float:
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
    ease: Callable[[float], float] = ease_smoothstep,
) -> np.ndarray:
    """Interpolate from start to a precomputed target layout.

    Uses an easing function to generate smooth transitions. This is a
    one-shot computation, not iterative.

    Args:
        start: Initial (N, 2) position array.
        target: Target (N, 2) position array.
        frames: Number of frames in the output history.
        ease: Easing function mapping [0, 1] -> [0, 1]. Defaults to
            ease_smoothstep.

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
def longest_path_depth(graph: nx.DiGraph) -> dict[int, int]:
    """Assign each node a layer via longest-path layering.

    A node's depth is one more than the maximum depth of its parents,
    which guarantees every edge points to a strictly deeper layer.

    Args:
        graph: A directed acyclic graph.

    Returns:
        A mapping from node id to layer index (root = 0).
    """
    depth: dict[int, int] = {}
    for node in nx.topological_sort(graph):
        parents = list(graph.predecessors(node))
        depth[node] = 1 + max(depth[p] for p in parents) if parents else 0
    return depth


# Setup (once): group_id, (N,) int array, -1 for the root
def branch_groups(graph: nx.DiGraph, root: int) -> npt.NDArray[np.int64]:
    """Assign each node the top-level branch it first descends from.

    Args:
        graph: A directed acyclic graph.
        root: The integer id of the root node.

    Returns:
        (N,) array of group indices; the root gets -1.
    """
    group = np.full(graph.number_of_nodes(), -1, dtype=np.int64)
    for gid, branch_root in enumerate(graph.successors(root)):
        for node in nx.bfs_tree(graph, branch_root):
            if group[node] == -1:
                group[node] = gid
    return group

# Setup (once): group_id, (N,) int array, -1 for the root
def branch_groups(graph: nx.DiGraph, root: int) -> npt.NDArray[np.int64]:
    """Assign each node the top-level branch it first descends from.

    Args:
        graph: A directed acyclic graph.
        root: The integer id of the root node.

    Returns:
        (N,) array of group indices; the root gets -1.
    """
    group = np.full(graph.number_of_nodes(), -1, dtype=np.int64)
    for gid, branch_root in enumerate(graph.successors(root)):
        for node in nx.bfs_tree(graph, branch_root):
            if group[node] == -1:
                group[node] = gid
    return group


def fr_step(
    pos: npt.NDArray[np.float64],
    edge_idx: npt.NDArray[np.int32],
    radial_target: npt.NDArray[np.float64],
    node_weight: npt.NDArray[np.float64],
    k: float,
    t: float,
    center: tuple[float, float] = (50.0, 50.0),
    gravity: float = 0.08,
    cohesion: float = 0.1,
    separation: float = 0.1,
    group_id: npt.NDArray[np.int64] | None = None,
) -> npt.NDArray[np.float64]:
    """Compute one Fruchterman-Reingold displacement with radial gravity.

    Repulsion between two nodes is scaled by the product of their
    weights, so high-degree nodes claim more space. Radial gravity
    pulls each node toward a ring around the center whose radius is
    set by the node's depth in the hierarchy.

    Args:
        pos: (N, 2) array of current node positions. Not modified.
        edge_idx: (E, 2) array of edge endpoint indices.
        radial_target: (N,) array of per-node target radii from layering.
        node_weight: (N,) array of repulsion weights, e.g. degree-based.
        k: Ideal edge length constant.
        t: Temperature; scales the soft displacement limit.
        center: The (x, y) point the rings are centered on.
        gravity: Spring strength pulling nodes toward their target ring.
        cohesion: Spring strength pulling nodes toward their group centroid.
        separation: Spring strength pushing group centroids apart.
        group_id: (N,) array of group indices for cohesion; -1 for nodes with no group.

    Returns:
        An (N, 2) displacement array, soft-limited by the temperature.
    """
    # Repulsion: all pairs, scaled per pair by the product of node weights.
    delta = pos[:, None, :] - pos[None, :, :]  # (N, N, 2)
    dist = np.maximum(np.linalg.norm(delta, axis=-1), 0.01)  # (N, N)
    pair_weight = node_weight[:, None] * node_weight[None, :]  # (N, N)
    disp = (delta / dist[..., None] * (pair_weight * k**2 / dist)[..., None]).sum(
        axis=1
    )

    # Attraction: per edge, scattered back to both endpoints.
    e_delta = pos[edge_idx[:, 0]] - pos[edge_idx[:, 1]]  # (E, 2)
    e_dist = np.maximum(np.linalg.norm(e_delta, axis=1), 0.01)  # (E,)
    pull = e_delta / e_dist[:, None] * (e_dist**2 / k)[:, None]
    np.add.at(disp, edge_idx[:, 0], -pull)
    np.add.at(disp, edge_idx[:, 1], pull)

    # Radial gravity: spring toward each node's target ring around center.
    from_center = pos - np.asarray(center)  # (N, 2)
    radius = np.maximum(np.linalg.norm(from_center, axis=1), 0.01)  # (N,)
    outward = from_center / radius[:, None]  # (N, 2) unit vectors
    disp += outward * (gravity * (radial_target - radius))[:, None]

    # Cohesion: pull toward own group's centroid.
    n_groups = group_id.max() + 1
    member = group_id >= 0
    centroids = np.zeros((n_groups, 2))
    np.add.at(centroids, group_id[member], pos[member])
    counts = np.bincount(group_id[member], minlength=n_groups)
    centroids /= counts[:, None]
    disp[member] += cohesion * (centroids[group_id[member]] - pos[member])

    # Separation: centroids repel each other; members inherit the push.
    c_delta = centroids[:, None, :] - centroids[None, :, :]  # (G, G, 2)
    c_dist = np.maximum(np.linalg.norm(c_delta, axis=-1), 0.01)  # (G, G)
    c_push = (c_delta / c_dist[..., None] * (separation * k**2 / c_dist)[..., None]).sum(
        axis=1
    )  # (G, 2)
    disp[member] += c_push[group_id[member]]

    # Soft temperature limit, per node.
    length = np.linalg.norm(disp, axis=1, keepdims=True)  # (N, 1)
    return disp * (t / (t + length))


# --- Initialize graph -----------------------------------------------------------------
fig, ax = create_figure()
graph_data: dict[str, Iterable[str]] = load_graph_data()
G = GraphView(fig, ax, nx.DiGraph(graph_data), axis_lim=(0, 100), spawn_margin=20)

# --- Main  ----------------------------------------------------------------------------
edge_idx = np.array(list(G.graph.edges), dtype=np.int32)

depth = longest_path_depth(G.graph)
n_layers = max(depth.values()) + 1
DR: float = 42 / max(n_layers - 1, 1)  # ring spacing; outermost ring at radius 42
radial_target = np.array(
    [depth[n] * DR for n in sorted(G.graph)], dtype=np.float64
)

degree = np.array([G.graph.degree[n] for n in sorted(G.graph)], dtype=np.float64)
node_weight = np.sqrt(degree / degree.mean())
velocity = np.zeros_like(G.pos)  # module level, next to the knobs

group_id = branch_groups(G.graph, root=0)

K: float = 4
T_INITIAL: float = 0.15
GRAVITY: float = 1
CENTER: tuple[float, float] = (50.0, 50.0)
MOMENTUM: float = 0.6
COHESION: float = 0.1
SEPARATION: float = 0.2


def animate(frame: int):
    """Advance the layout by one Fruchterman-Reingold iteration.

    Args:
        frame: The current frame index, which drives the cooling schedule.

    Returns:
        The node and edge artists for blitting.
    """
    global velocity
    t = T_INITIAL * (1 - ease_smoothstep(frame / FRAMES))
    
    step = fr_step(G.pos, edge_idx, radial_target, node_weight, K, t, CENTER, GRAVITY, COHESION, SEPARATION, group_id=group_id)
    
    velocity = MOMENTUM * velocity + step  # MOMENTUM ~ 0.5-0.7
    G.pos = np.clip(G.pos + velocity, 0, 100)

    return G.get_artists()


anim = FuncAnimation(
    fig, func=animate, interval=INTERVAL_MS, frames=FRAMES, repeat=False, blit=True
)
# save animation as mp4
# anim.save("animation.mp4", writer="ffmpeg")

plt.tight_layout()
plt.show()
