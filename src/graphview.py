from collections.abc import Iterable

import networkx as nx
import numpy as np
import numpy.typing as npt
import yaml
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D
from mpl_toolkits.mplot3d import proj3d
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Path3DCollection
from mpl_toolkits.mplot3d.axes3d import Axes3D
from numpy import float64
from numpy._typing._array_like import NDArray

from src.mpl_utils import COLOR_EDGES, COLOR_NODES

NodeName = str
GraphAttr = dict[str, object]
NodeAttr = dict[str, object]

# Alpha of the farthest label; nearest labels are fully opaque.
LABEL_MIN_ALPHA = 0.25


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


class ScreenSpaceLabels(PathCollection):
    """Batched 2D text paths that can live on a 3D axes.

    Axes3D.draw calls do_3d_projection() on every Collection child, so a
    plain PathCollection crashes the draw. Offsets are node positions
    projected into the axes' 2D data space, recomputed by
    GraphView.refresh() each frame.
    """

    def do_3d_projection(self) -> float:
        """Report depth to Axes3D.

        Returns:
            -inf, i.e. nearest, so the labels sort on top if
            computed_zorder is ever enabled. Ignored with
            computed_zorder=False.
        """
        return -np.inf


class GraphView:
    """Renders a fixed-topology DiGraph whose nodes are integers 0..N-1.

    Node id == row in the position array, so geometry (self._pos) and topology
    (self.graph) stay aligned by construction, with no separate index map.
    """

    def __init__(
        self,
        fig: Figure,
        ax: Axes3D,
        graph: nx.DiGraph,
        *,
        axis_lim: tuple[int, int] = (0, 100),
        spawn_margin: int = 20,
        rng: np.random.Generator | None = None,
    ) -> None:
        """Initialise GraphView with a figure, 3D axes, and directed graph.

        Relabels nodes to integers 0..N-1 and initialises random positions.

        Args:
            fig: The Matplotlib figure to render into.
            ax: The Matplotlib 3D axes to render into.
            graph: The directed graph to visualise.
            axis_lim: (low, high) bounds for the axes; used to compute the
                spawn range.
            spawn_margin: Margin subtracted from axis_lim to keep spawned
                nodes away from the edge.
            rng: Optional random generator for node positions. Defaults to a
                fixed-seed generator if not provided.
        """
        self.fig: Figure = fig
        self.ax: Axes3D = ax
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
        self._pos: NDArray[float64] = rng.uniform(low, high, size=(n, 3))

        # Create Matplotlib objects for nodes and edges. The axes has
        # computed_zorder=False, so draw order is fixed: edges under
        # nodes under labels, stable across camera angles.
        self._scatter: Path3DCollection = ax.scatter(
            self._pos[:, 0],
            self._pos[:, 1],
            self._pos[:, 2],
            color=COLOR_NODES,
            zorder=2,
        )
        self._edge_lines: Line3DCollection = Line3DCollection(
            self._pos[self._edge_idx], color=COLOR_EDGES, linewidths=1, zorder=1
        )
        _ = self.ax.add_collection3d(self._edge_lines)

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

        offsets, _depth = self._label_screen_coords()
        self._label_collection: ScreenSpaceLabels = ScreenSpaceLabels(
            label_paths,
            offsets=offsets,
            offset_transform=ax.transData,
            transform=Affine2D().scale(fig.dpi / 72),
            facecolor="white",
            edgecolor="white",
            linewidth=1,
            joinstyle="round",
            capstyle="round",
            zorder=3,
        )
        _ = self.ax.add_collection(self._label_collection, autolim=False)
        self.refresh()

    @property
    def pos(self) -> npt.NDArray[np.float64]:
        """(N, 3) array of current node positions, one row per node."""
        return self._pos

    @pos.setter
    def pos(self, new_pos: npt.NDArray[np.float64]) -> None:
        """Set node positions and update the rendered artists.

        Args:
            new_pos: (N, 3) array of new node positions.
        """
        self._pos = new_pos
        self.refresh()

    def layout_from(
        self, layout: dict[int, tuple[float, float, float] | npt.ArrayLike]
    ) -> None:
        """Accept a finished 3D layout dict and apply it via the pos setter.

        3D-capable layout functions (nx.spring_layout with dim=3, fa2's
        forceatlas2_networkx_layout with dim=3, etc.) return
        {node: (x, y, z)} dicts keyed by the original node labels. After
        the integer relabel in __init__, node id == row in the position
        array, so the dict values can be stacked directly into an (N, 3)
        array.

        Args:
            layout: A {node: (x, y, z)} dict as returned by a layout function.
        """
        self.pos = np.array(list(layout.values()))

    def _label_screen_coords(
        self,
    ) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        """Project node positions into the axes' 2D data space.

        Text3D.draw applies this same projection per label per draw;
        doing it here for all nodes at once keeps the labels in a single
        batched artist.

        Returns:
            An ((N, 2) offsets, (N,) depth) tuple, where larger depth is
            farther from the camera.
        """
        xs, ys, depth = proj3d.proj_transform(
            self._pos[:, 0], self._pos[:, 1], self._pos[:, 2], self.ax.get_proj()
        )
        return np.column_stack([xs, ys]), depth

    def refresh(self) -> None:
        """Push the current position array into the Matplotlib artists.

        Call after making in-place edits to self._pos, and after any
        camera move: label offsets go through the current view matrix, so
        change the camera (ax.view_init) before refreshing or the labels
        lag one frame. No new artists are created; the existing
        collections are updated.
        """
        # 3D scatter has no working set_offsets; assigning the
        # (xs, ys, zs) tuple is the supported update path.
        self._scatter._offsets3d = tuple(self._pos.T)
        self._edge_lines.set_segments(self._pos[self._edge_idx])
        offsets, depth = self._label_screen_coords()
        self._label_collection.set_offsets(offsets)
        # Depth cueing: fade labels with distance from the camera.
        far = (depth - depth.min()) / max(np.ptp(depth), 1e-9)
        self._label_collection.set_alpha(
            LABEL_MIN_ALPHA + (1.0 - LABEL_MIN_ALPHA) * (1.0 - far)
        )

    def move_node(self, node: int, xyz: npt.ArrayLike) -> None:
        """Set the position of a single node without refreshing the artists.

        Args:
            node: The integer node id (0..N-1).
            xyz: The new (x, y, z) coordinate for the node.
        """
        self._pos[node] = xyz

    def get_node_coords(self, node: int) -> npt.NDArray[np.float64]:
        """Return the current (x, y, z) position of a single node.

        Args:
            node: The integer node id (0..N-1).

        Returns:
            A 1-D array of shape (3,) with the node's coordinates.
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
    ) -> tuple[Path3DCollection, Line3DCollection, ScreenSpaceLabels]:
        """Return the node, edge, and label artists.

        Returns:
            A (Path3DCollection, Line3DCollection, ScreenSpaceLabels)
            tuple with the node scatter, the edge line collection, and
            the node labels.
        """
        return (self._scatter, self._edge_lines, self._label_collection)
