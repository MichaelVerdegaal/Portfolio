from matplotlib.figure import Figure


from networkx.classes.digraph import DiGraph


from collections.abc import Iterable

import networkx as nx
from src.mpl_utils import create_figure
import numpy as np
import numpy.typing as npt
import yaml
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.figure import Figure
from matplotlib import pyplot as plt
from src.mpl_utils import COLOR_EDGES, COLOR_NODES


NodeName = str
GraphAttr = dict[str, object]
NodeAttr = dict[str, object]



def random_coordinates(
    G: nx.Graph,
    axis_lim: tuple[int, int] = (0, 100),
    spawn_margin: int = 20,
    dim: int = 2,
    rng: np.random.Generator | None = None,
) -> dict[NodeName, npt.NDArray[np.float64]]:
    """Random node positions on [axis_lim + spawn_margin] per coordinate.

    Returns a dict keyed by node (like nx.random_layout). If store_pos_as is
    given, also writes each position to that node attribute.
    """
    rng = rng if rng is not None else np.random.default_rng(3)
    low, high = axis_lim[0] + spawn_margin, axis_lim[1] - spawn_margin
    coords = rng.uniform(low, high, size=(G.number_of_nodes(), dim))
    pos = dict(zip(G, coords))
    nx.set_node_attributes(G, pos, "pos")
    return pos


class MPLGraph(nx.DiGraph):
    """
    Example subclass of the Graph class.

    Prints activity log to file or standard output.
    """

    def __init__(self, fig: Figure, ax: Axes, layout: npt.ArrayLike | None = None, **kwargs):
        super().__init__(**kwargs)
        self.fig: Figure = fig
        self.ax: Axes = ax

        # Indices of nodes in the graph, used to index into the layout array
        self.index: dict[str, int] = {name: i for i, name in enumerate(self.nodes)}
        self._edges: npt.NDArray[np.int32] = np.array(
            [(self.index[u], self.index[v]) for u, v in self.edges()],
            dtype=np.int32,
        ).reshape(-1, 2)

        # Coordinates
        if layout is None:
            pos = random_coordinates(self)
            self.layout = np.array(list(pos.values()), dtype=np.float64)
        else:
            self.layout = np.array(layout, dtype=np.float64)


        # Add nodes and edges to axes
        self.scatter: PathCollection = self.ax.scatter(
            self.layout[:, 0], self.layout[:, 1], color=COLOR_NODES, zorder=2
        )
        self.edge_lines: LineCollection = LineCollection(
            self.layout[self._edges], color=COLOR_EDGES, linewidths=1, zorder=1
        )
        self.ax.add_collection(self.edge_lines)

    def add_node(self, n, attr_dict=None, **kwargs):
        super().add_node(n, attr_dict=attr_dict, **kwargs)

    def add_nodes_from(self, nodes, **kwargs):
        for n in nodes:
            self.add_node(n, **kwargs)

    def remove_node(self, n):
        super().remove_node(n)

    def remove_nodes_from(self, nodes):
        for n in nodes:
            self.remove_node(n)

    def add_edge(self, u, v, attr_dict=None, **kwargs):
        super().add_edge(u, v, attr_dict=attr_dict, **kwargs)

    def add_edges_from(self, ebunch, attr_dict=None, **kwargs):
        for e in ebunch:
            u, v = e[0:2]
            self.add_edge(u, v, attr_dict=attr_dict, **kwargs)

    def remove_edge(self, u, v):
        super().remove_edge(u, v)

    def remove_edges_from(self, ebunch):
        for e in ebunch:
            u, v = e[0:2]
            self.remove_edge(u, v)

    def clear(self):
        super().clear()


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



def random_layout(G: nx.Graph, seed: int | None = None) -> npt.NDArray[np.float32]:
    """Return a random layout for the graph G."""
    layout: dict[str, npt.NDArray[np.float32]] = nx.random_layout(G, seed=seed)
    return np.array(list(layout.values()), dtype=np.float32)


# Instantiate graph and initial layout
fig, ax = create_figure()
graph_data: dict[str, Iterable[str]] = load_graph_data()
G = MPLGraph(incoming_graph_data=graph_data, fig=fig, ax=ax)

plt.show()

