"""Graph layout utilities using ForceAtlas2."""

import networkx as nx
import numpy as np
import numpy.typing as npt
from fa2 import ForceAtlas2

from .graphview import GraphView

AXIS_MIN = 0
AXIS_MAX = 100


def rescale_uniform(coords: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Rescale a set of 2D/3D coordinates to fit within [lo, hi] uniformly.

    Args:
        coords: An (N, 2|3) array of coordinates.
        lo: The lower bound of the target range.
        hi: The upper bound of the target range.

    Returns:
        An (N, 2|3) array of rescaled coordinates within [lo, hi].
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
        is_3d: Whether to compute a 3D layout.

    Returns:
        An (N, 2) | (N, 3) array of target positions for the graph nodes.
    """
    pos = graph_view.pos.copy()
    G_sparse = nx.to_scipy_sparse_array(graph_view.graph.to_undirected())

    fa2: ForceAtlas2 = ForceAtlas2.inferSettings(
        G_sparse, seed=3, verbose=False, backend="vectorized", dim=3 if is_3d else 2
    )
    layout = fa2.forceatlas2(G_sparse, pos=pos, iterations=100)

    layout_np = np.array(layout)
    return rescale_uniform(layout_np, AXIS_MIN + 3, AXIS_MAX - 3)
