from collections.abc import Iterable

import networkx as nx
import numpy as np
import numpy.typing as npt
import yaml
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Path3DCollection
from mpl_toolkits.mplot3d.axes3d import Axes3D
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


class TextPathCollection3D(PathCollection):
    def __init__(
        self,
        paths: list[Path],
        positions: npt.NDArray[np.float64],
        *,
        color: str = "white",
        alpha_range: tuple[float, float] = (0.3, 1.0),
        **kwargs: object,
    ) -> None:
        """Initialise the collection with per-label paths and 3D anchors.

        Args:
            paths: One glyph path per label, in node order.
            positions: (N, 3) array of anchor points in data coordinates.
            color: Base colour for the glyph fill and stroke.
            alpha_range: (far, near) alpha applied across the depth range.
            **kwargs: Styling forwarded to PathCollection.
        """
        super().__init__(paths, offsets=np.zeros((len(paths), 2)), **kwargs)
        self._positions3d: npt.NDArray[np.float64] = positions
        self._base_rgba: npt.NDArray[np.float64] = np.array(to_rgba(color))
        self._alpha_range: tuple[float, float] = alpha_range

    def _depth_rgba(self, depth: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        """Map projected depth to per-label RGBA.

        Args:
            depth: (N,) projected depths, larger values further from the camera.

        Returns:
            (N, 4) RGBA array in label order.
        """
        span = float(depth.max() - depth.min())
        far_alpha, near_alpha = self._alpha_range
        t = np.zeros_like(depth) if span < 1e-12 else (depth - depth.min()) / span
        rgba = np.tile(self._base_rgba, (len(depth), 1))
        rgba[:, 3] = near_alpha - t * (near_alpha - far_alpha)
        return rgba

    def set_positions(self, positions: npt.NDArray[np.float64]) -> None:
        """Replace the 3D anchor points.

        Args:
            positions: (N, 3) array of anchor points in data coordinates.
        """
        self._positions3d = positions

    def do_3d_projection(self) -> float:
        homogeneous = np.column_stack(
            [self._positions3d, np.ones(len(self._positions3d))]
        )
        projected = homogeneous @ self.axes.M.T
        projected = projected[:, :3] / projected[:, 3, None]
        self.set_offsets(projected[:, :2])

        if not projected.size:
            return float("nan")

        depth = projected[:, 2]
        rgba = self._depth_rgba(depth)
        self.set_facecolor(rgba)
        self.set_edgecolor(rgba)
        return float(depth.min())


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
        self._is_3d: bool = is_3d
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
        label_font = FontProperties(size=10)
        label_paths = []
        for node in self.graph:
            text_path = TextPath(
                (0, 0), str(self.graph.nodes[node]["name"]), prop=label_font
            )
            extents = text_path.get_extents()
            # Anchor: centered horizontally, 4pt above the node
            anchor = Affine2D().translate(-extents.width / 2 - extents.x0, 4)
            label_paths.append(anchor.transform_path(text_path))

        if self._is_3d:
            self._label_collection = TextPathCollection3D(
                label_paths,
                self._pos,
                offset_transform=ax.transData,
                transform=Affine2D().scale(fig.dpi / 72),
                facecolor="white",
                edgecolor="white",
                linewidth=1,
                joinstyle="round",
                capstyle="round",
                zorder=3,
            )
            _ = ax.add_collection(self._label_collection, autolim=False)
        else:
            self._label_collection: PathCollection = PathCollection(
                label_paths,
                offsets=self._pos[:, :2],
                offset_transform=ax.transData,
                transform=Affine2D().scale(fig.dpi / 72),
                facecolor="white",
                edgecolor="white",
                linewidth=1,
                joinstyle="round",
                capstyle="round",
                zorder=2,
            )
            _ = ax.add_collection(self._label_collection)

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
        if self._is_3d:
            self._scatter._offsets3d = tuple(self._pos.T)
            self._edge_lines.set_segments(self._pos[self._edge_idx])
            self._label_collection.set_positions(self._pos)
        else:
            self._scatter.set_offsets(self._pos)
            self._edge_lines.set_segments(self._pos[self._edge_idx])
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
    ) -> tuple[
        PathCollection | Path3DCollection,
        LineCollection | Line3DCollection,
        PathCollection | Path3DCollection,
    ]:
        """Return the node, edge, and label artists for animation blitting.

        Returns:
            A (scatter, edges, labels) tuple with the node scatter, the edge
            line collection, and the label collection.
        """
        return (self._scatter, self._edge_lines, self._label_collection)
