from collections.abc import Iterable

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import numpy.typing as npt
import yaml
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.figure import Figure

from src.mpl_utils import COLOR_EDGES, COLOR_NODES, create_figure


class GraphView:
    """Renders a fixed-topology DiGraph whose nodes are integers 0..N-1.

    Node id == row in the position array, so geometry (self._pos) and topology
    (self.graph) stay aligned by construction, with no separate index map.
    """

    def __init__(
        self,
        fig: Figure,
        ax: Axes,
        graph: nx.DiGraph,
        *,
        axis_lim: tuple[int, int] = (0, 100),
        spawn_margin: int = 20,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.fig: Figure = fig
        self.ax: Axes = ax
        # Set labels of the nodes to integer to support rapid indexing
        self.graph: nx.DiGraph = nx.convert_node_labels_to_integers(
            graph, label_attribute="name"
        )

        # node id is the row, so edges are already index pairs
        self._edge_idx: npt.NDArray[np.int32] = np.array(
            list(self.graph.edges), dtype=np.int32
        ).reshape(-1, 2)

        # Initialize random coordinates for each node
        rng = rng or np.random.default_rng(3)
        low, high = axis_lim[0] + spawn_margin, axis_lim[1] - spawn_margin
        n: int = self.graph.number_of_nodes()
        self._pos = rng.uniform(low, high, size=(n, 2))

        # Create Matplotlib objects for nodes and edges
        self._scatter: PathCollection = ax.scatter(
            self._pos[:, 0], self._pos[:, 1], color=COLOR_NODES, zorder=2
        )
        self._edge_lines: LineCollection = LineCollection(
            self._pos[self._edge_idx], color=COLOR_EDGES, linewidths=1, zorder=1
        )
        _ = self.ax.add_collection(self._edge_lines)

    @property
    def pos(self) -> npt.NDArray[np.float64]:
        return self._pos

    @pos.setter
    def pos(self, new_pos: npt.NDArray[np.float64]) -> None:
        self._pos = new_pos
        self.refresh()

    def refresh(self) -> None:
        """Push the current array to the collections. Call after in-place edits."""
        self._scatter.set_offsets(self._pos)
        self._edge_lines.set_segments(self._pos[self._edge_idx])

    def move_node(self, node: int, xy: npt.ArrayLike) -> None:
        self._pos[node] = xy

    def get_node_coords(self, node: int) -> npt.NDArray[np.float64]:
        return self._pos[node]

    def sync_to_graph(self) -> None:
        """Write the array back into node 'pos' attributes. Deliberate, not per-frame."""
        nx.set_node_attributes(self.graph, {n: self._pos[n] for n in self.graph}, "pos")


def load_graph_data() -> dict[str, Iterable[str]]:
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
    return adjacency


# Instantiate graph and initial layout
fig, ax = create_figure()
graph_data: dict[str, Iterable[str]] = load_graph_data()
G = GraphView(fig, ax, nx.DiGraph(graph_data), axis_lim=(0, 100), spawn_margin=20)

print(G.get_node_coords(0))
plt.show()
