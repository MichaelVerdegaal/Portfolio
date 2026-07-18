from collections.abc import Iterable
from numpy._typing._array_like import NDArray
from numpy import float64
import matplotlib.patheffects as pe
import networkx as nx
import numpy as np
import numpy.typing as npt
import yaml
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.figure import Figure
from matplotlib.text import Annotation

from src.mpl_utils import COLOR_EDGES, COLOR_NODES, COLOR_BG

NodeName = str
GraphAttr = dict[str, object]
NodeAttr = dict[str, object]


def load_graph_data() -> dict[str, Iterable[str]]:
    """Load an adjacency-list graph from YAML, preserving parent -> child direction.

    Each YAML entry is either a bare node name or a {name: [children]} mapping.

    Returns:
        A dictionary mapping each node name to an iterable of its child node names.
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
        """Initialise GraphView with a figure, axes, and directed graph.

        Relabels nodes to integers 0..N-1 and initialises random positions.

        Args:
            fig: The Matplotlib figure to render into.
            ax: The Matplotlib axes to render into.
            graph: The directed graph to visualise.
            axis_lim: (low, high) bounds for the axes; used to compute the
                spawn range.
            spawn_margin: Margin subtracted from axis_lim to keep spawned
                nodes away from the edge.
            rng: Optional random generator for node positions. Defaults to a
                fixed-seed generator if not provided.
        """
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
        self._pos: NDArray[float64] = rng.uniform(low, high, size=(n, 2))

        # Create Matplotlib objects for nodes and edges
        self._scatter: PathCollection = ax.scatter(
            self._pos[:, 0], self._pos[:, 1], color=COLOR_NODES, zorder=1
        )
        self._edge_lines: LineCollection = LineCollection(
            self._pos[self._edge_idx], color=COLOR_EDGES, linewidths=1, zorder=3
        )
        _ = self.ax.add_collection(self._edge_lines)

        # Labels above the nodes
        self._labels: list[Annotation] = [
            ax.annotate(
                str(self.graph.nodes[node]["name"]),
                xy=self._pos[node],
                xytext=(-3, 3),
                textcoords="offset points",
                horizontalalignment="right",
                verticalalignment="bottom",
                color="white",
                zorder=2,
                path_effects=[pe.withStroke(linewidth=2.5, foreground=COLOR_BG)],
            )
            for node in self.graph
        ]

    @property
    def pos(self) -> npt.NDArray[np.float64]:
        """(N, 2) array of current node positions, one row per node."""
        return self._pos

    @pos.setter
    def pos(self, new_pos: npt.NDArray[np.float64]) -> None:
        """Set node positions and update the rendered artists.

        Args:
            new_pos: (N, 2) array of new node positions.
        """
        self._pos = new_pos
        self.refresh()

    def refresh(self) -> None:
        """Push the current position array into the Matplotlib collections.

        Call after making in-place edits to self._pos. No new artists are
        created; the existing scatter and line collection are updated.
        """
        self._scatter.set_offsets(self._pos)
        self._edge_lines.set_segments(self._pos[self._edge_idx])
        for node, label in enumerate(self._labels):
            label.xy = self._pos[node]

    def move_node(self, node: int, xy: npt.ArrayLike) -> None:
        """Set the position of a single node without refreshing the artists.

        Args:
            node: The integer node id (0..N-1).
            xy: The new (x, y) coordinate for the node.
        """
        self._pos[node] = xy

    def get_node_coords(self, node: int) -> npt.NDArray[np.float64]:
        """Return the current (x, y) position of a single node.

        Args:
            node: The integer node id (0..N-1).

        Returns:
            A 1-D array of shape (2,) with the node's x and y coordinates.
        """
        return self._pos[node]

    def sync_to_graph(self) -> None:
        """Write the current position array into node 'pos' attributes.

        This is a deliberate persistence step, not intended to be called
        every frame. After this call, nx.draw can read positions from the
        graph as node attributes.

        Raises:
            NetworkXError: If a node cannot be found in the graph (should
                never happen since node ids match array rows).
        """
        nx.set_node_attributes(self.graph, {n: self._pos[n] for n in self.graph}, "pos")

    def get_artists(self) -> tuple[PathCollection, LineCollection]:
        """Return the node and edge artists for use in animation blitting.

        Returns:
            A (PathCollection, LineCollection, Annotation...) tuple with the node scatter,
            the edge line collection, and the node labels.
        """
        return (self._scatter, self._edge_lines, *self._labels)
