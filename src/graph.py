from __future__ import annotations

from collections.abc import Iterable

import networkx as nx
import numpy as np
import numpy.typing as npt
import yaml
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.figure import Figure

from src.mpl_utils import COLOR_EDGES, COLOR_NODES

NodeName = str
GraphAttr = dict[str, object]
NodeAttr = dict[str, object]


def load_graph_data() -> nx.DiGraph[NodeName, NodeAttr, GraphAttr]:
    """Load an adjacency-list graph from YAML, preserving parent -> child direction.

    Each YAML entry is either a bare node name or a {name: [children]} mapping.
    """
    with open("src/graph.yaml") as file:
        entries: list[str | dict[str, list[str]]] = yaml.safe_load(file)
    adjacency: dict[str, Iterable[str]] = {}
    for entry in entries:
        if isinstance(entry, dict):
            adjacency.update(entry)
        else:
            adjacency[entry] = []
    return nx.from_dict_of_lists(adjacency, create_using=nx.DiGraph)


class GraphView:
    def __init__(
        self,
        fig: Figure,
        ax: Axes,
        graph: nx.DiGraph[NodeName, NodeAttr, GraphAttr],
        axis_lim: tuple[int, int] = (0, 100),
        spawn_margin: int = 20,
        rng: np.random.Generator | None = None,
    ) -> None:
        """Renders a NetworkX graph as matplotlib node/edge collections.

        Topology lives in `self.graph`; query it directly (self.graph.successors(n),
        self.graph.degree, nx.shortest_path(...)). Geometry lives in `self._pos`,
        kept in node order, which drives the two collections during animation.
        """
        self.fig: Figure = fig
        self.ax: Axes = ax
        self.graph: nx.DiGraph[NodeName, NodeAttr, GraphAttr] = graph
        self.index: dict[str, int] = {name: i for i, name in enumerate(graph)}

        self._edges: npt.NDArray[np.int32] = np.array(
            [(self.index[u], self.index[v]) for u, v in graph.edges()],
            dtype=np.int32,
        ).reshape(-1, 2)

        rng = rng if rng is not None else np.random.default_rng(3)
        low, high = axis_lim[0] + spawn_margin, axis_lim[1] - spawn_margin
        self._pos: npt.NDArray[np.float64] = rng.uniform(
            low, high, size=(graph.number_of_nodes(), 2)
        )

        self._scatter: PathCollection = ax.scatter(
            self._pos[:, 0], self._pos[:, 1], color=COLOR_NODES, zorder=2
        )
        self._edge_lines: LineCollection = LineCollection(
            self._pos[self._edges], color=COLOR_EDGES, linewidths=1, zorder=1
        )
        _ = ax.add_collection(self._edge_lines)

    @property
    def pos(self) -> npt.NDArray[np.float64]:
        return self._pos

    @pos.setter
    def pos(self, new_pos: npt.NDArray[np.float64]) -> None:
        self._pos = new_pos
        self._scatter.set_offsets(new_pos)
        self._edge_lines.set_segments(new_pos[self._edges])

    @property
    def edge_lengths(self) -> npt.NDArray[np.float64]:
        delta = self._pos[self._edges[:, 1]] - self._pos[self._edges[:, 0]]
        return np.hypot(delta[:, 0], delta[:, 1])

    def get_artists(self) -> tuple[PathCollection, LineCollection]:
        return self._scatter, self._edge_lines

    def move_node(self, name: str, new_coords: npt.ArrayLike) -> None:
        self._pos[self.index[name]] = new_coords
        self._scatter.set_offsets(self._pos)
        self._edge_lines.set_segments(self._pos[self._edges])

    def get_node_coords(self, name: str) -> npt.NDArray[np.float64] | None:
        """Return the X-Y coordinates of a node by name."""
        index = self.index.get(name)
        if index is not None:
            return self._pos[index]
        return None
