from collections.abc import Iterable
from mpl_toolkits.mplot3d.axes3d import Axes3D
import networkx as nx
import numpy as np
import numpy.typing as npt
import yaml
from matplotlib.axes import Axes
from mpl_toolkits.mplot3d.art3d import Path3DCollection
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from numpy import float64
from numpy._typing._array_like import NDArray

from src.mpl_utils import COLOR_EDGES, COLOR_NODES

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
        ax: Axes | Axes3D,
        graph: nx.DiGraph,
        *,
        axis_lim: tuple[int, int] = (0, 100),
        spawn_margin: int = 20,
        is_3d: bool = False,
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
            is_3d: If true, assumes 3D coordinates and plotting
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
        rng = np.random.default_rng(3)
        low, high = axis_lim[0] + spawn_margin, axis_lim[1] - spawn_margin
        n: int = self.graph.number_of_nodes()
        coord_dim = (n, 3) if is_3d else (n, 2)
        self._pos: NDArray[float64] = rng.uniform(low, high, size=coord_dim)

        # Create Matplotlib objects for nodes and edges
        if is_3d:
            self._scatter: Path3DCollection = ax.scatter(
                self._pos[:, 0],
                self._pos[:, 1],
                self._pos[:, 2],
                color=COLOR_NODES,
            )
            self._edge_lines: Line3DCollection = Line3DCollection(
                self._pos[self._edge_idx], color=COLOR_EDGES, linewidths=1
            )
            _ = self.ax.add_collection3d(self._edge_lines)
        else:
            self._scatter: PathCollection = ax.scatter(
                self._pos[:, 0], self._pos[:, 1], color=COLOR_NODES, zorder=1
            )
            self._edge_lines: LineCollection = LineCollection(
                self._pos[self._edge_idx], color=COLOR_EDGES, linewidths=1, zorder=3
            )
            _ = self.ax.add_collection(self._edge_lines)

        # Labels above the nodes
        # label_font = FontProperties(size=10)
        # label_paths = []
        # for node in self.graph:
        #     text_path = TextPath(
        #         (0, 0), str(self.graph.nodes[node]["name"]), prop=label_font
        #     )
        #     extents = text_path.get_extents()
        #     # Anchor: centered horizontally, 4pt above the node
        #     anchor = Affine2D().translate(-extents.width / 2 - extents.x0, 4)
        #     label_paths.append(anchor.transform_path(text_path))

        # self._label_collection: PathCollection = PathCollection(
        #     label_paths,
        #     offsets=self._pos,
        #     offset_transform=ax.transData,
        #     transform=Affine2D().scale(fig.dpi / 72),
        #     facecolor="white",
        #     edgecolor="white",
        #     linewidth=1,
        #     joinstyle="round",
        #     capstyle="round",
        #     zorder=2,
        # )
        # _ = ax.add_collection(self._label_collection)

    @property
    def pos(self) -> npt.NDArray[np.float64]:
        """(N, 2) | (N, 3) array of current node positions, one row per node."""
        return self._pos

    @pos.setter
    def pos(self, new_pos: npt.NDArray[np.float64]) -> None:
        """Set node positions and update the rendered artists.

        Args:
            new_pos: (N, 2) | (N, 3) array of new node positions.
        """
        self._pos = new_pos
        self.refresh()

    def layout_from(
        self, layout: dict[int, tuple[float, float] | npt.ArrayLike]
    ) -> None:
        """Accept a finished NetworkX layout dict and apply it via the pos setter.

        NetworkX layout functions (nx.circular_layout, nx.spring_layout, etc.)
        return {node: (x, y)} dicts keyed by the original node labels.  After
        the integer relabel in __init__, node id == row in the position array,
        so the dict values can be stacked directly into an (N, 2) array.

        Args:
            layout: A {node: (x, y)} dict as returned by nx.layout_*.
        """
        self.pos = np.array(list(layout.values()))

    def refresh(self) -> None:
        """Push the current position array into the Matplotlib collections.

        Call after making in-place edits to self._pos. No new artists are
        created; the existing scatter and line collection are updated.
        """
        if self._pos.shape[1] == 3:
            self._scatter._offsets3d = tuple(self._pos.T)
        else:
            self._scatter.set_offsets(self._pos)

        self._edge_lines.set_segments(self._pos[self._edge_idx])

        if hasattr(self, "_label_collection"):
            self._label_collection.set_offsets(self._pos)

    def move_node(self, node: int, xy: npt.ArrayLike) -> None:
        """Set the position of a single node without refreshing the artists.

        Args:
            node: The integer node id (0..N-1).
            xy: The new (x, y) | (x, y, z) coordinate for the node.
        """
        self._pos[node] = xy

    def get_node_coords(self, node: int) -> npt.NDArray[np.float64]:
        """Return the current (x, y) position of a single node.

        Args:
            node: The integer node id (0..N-1).

        Returns:
            A 1-D array of shape (2,) | (3,) with the node's coordinates.
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

    def get_artists(
        self,
    ) -> tuple[PathCollection | Path3DCollection, LineCollection | Line3DCollection]:
        """Return the node and edge artists for use in animation blitting.

        Returns:
            A (PathCollection, LineCollection) tuple with the node scatter and
            the edge line collection. Includes the label collection if labels
            are enabled.
        """
        artists: tuple[
            PathCollection | Path3DCollection,
            LineCollection | Line3DCollection,
        ] = (self._scatter, self._edge_lines)
        if hasattr(self, "_label_collection"):
            artists = artists + (self._label_collection,)
        return artists
