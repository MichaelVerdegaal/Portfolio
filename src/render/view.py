"""The Graph view composes matplotlib artists for a fixed-topology graph."""

import networkx as nx
import numpy as np
import numpy.typing as npt
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Path3DCollection
from mpl_toolkits.mplot3d.axes3d import Axes3D

from ..config import (
    ACCENT_HALO,
    ACCENT_NODE,
    ACCENT_NODE_COUNT,
    ACCENT_SIZE_SCALE,
    COLOR_ACCENT,
    COLOR_EDGES,
    COLOR_INK,
    COLOR_NODES,
    EDGE_ALPHA_FAR,
    EDGE_ALPHA_NEAR,
    EDGE_FADE_GAMMA,
    EDGE_LENGTH_FALLOFF,
    HALO_LINEWIDTH,
    HALO_SIZE,
    INK_EDGE,
    INK_NODE,
    LABEL_FONT_SIZE,
    NODE_SIZE,
    NODE_SIZE_JITTER,
    RNG_SEED,
    SIZE_SEED,
)
from .artists import EdgeCollection3D, TextPathCollection3D


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
        rng = np.random.default_rng(RNG_SEED)
        low, high = axis_lim[0] + spawn_margin, axis_lim[1] - spawn_margin
        n: int = self.graph.number_of_nodes()
        # Highest-degree nodes get the accent treatment. Degree is stable across
        # runs, unlike a random pick, so the same nodes are emphasised each render.
        degrees = np.array([self.graph.degree(node) for node in range(n)])
        accent_count = min(ACCENT_NODE_COUNT, n)
        self._accent_mask: npt.NDArray[np.bool_] = np.zeros(n, dtype=bool)
        if accent_count:  # A [-0:] slice would select every node, not none.
            self._accent_mask[np.argsort(degrees)[-accent_count:]] = True
        size_rng = np.random.default_rng(SIZE_SEED)
        node_sizes = NODE_SIZE * size_rng.uniform(
            1.0 - NODE_SIZE_JITTER, 1.0 + NODE_SIZE_JITTER, n
        )
        node_sizes[self._accent_mask] *= ACCENT_SIZE_SCALE
        coord_dim = (n, 3) if is_3d else (n, 2)
        self._pos: npt.NDArray[np.float64] = rng.uniform(low, high, size=coord_dim)

        # Create Matplotlib objects for nodes and edges
        if is_3d:
            node_colors = np.tile(to_rgba(COLOR_INK, INK_NODE), (n, 1))
            node_colors[self._accent_mask] = to_rgba(COLOR_ACCENT, ACCENT_NODE)
            self._node_colors: npt.NDArray[np.float64] = node_colors
            self._scatter: Path3DCollection = ax.scatter(
                self._pos[:, 0],
                self._pos[:, 1],
                self._pos[:, 2],
                s=node_sizes,
                color=node_colors,
                # Depth shading would fold a second, implicit alpha curve into
                # the nodes that the halos (depthshade=False) never get, so the
                # two would drift apart as they breathe. Edges and labels carry
                # the depth cue explicitly instead.
                depthshade=False,
            )

            halo_pos = self._pos[self._accent_mask]
            self._halo: Path3DCollection = ax.scatter(
                halo_pos[:, 0],
                halo_pos[:, 1],
                halo_pos[:, 2],
                s=HALO_SIZE,
                facecolors="none",
                edgecolors=to_rgba(COLOR_ACCENT, ACCENT_HALO),
                linewidths=HALO_LINEWIDTH,
                depthshade=False,
            )
            self._edge_lines: Line3DCollection = EdgeCollection3D(
                self._pos[self._edge_idx],
                color=COLOR_INK,
                base_alpha=INK_EDGE,
                length_falloff=EDGE_LENGTH_FALLOFF,
                depth_range=(EDGE_ALPHA_FAR, EDGE_ALPHA_NEAR),
                gamma=EDGE_FADE_GAMMA,
                linewidths=1,
            )
            _ = self.ax.add_collection3d(self._edge_lines)
        else:
            self._halo: Path3DCollection | None = None
            self._scatter: PathCollection = ax.scatter(
                self._pos[:, 0], self._pos[:, 1], color=COLOR_NODES, zorder=1
            )
            self._edge_lines: LineCollection = LineCollection(
                self._pos[self._edge_idx],
                color=to_rgba(COLOR_EDGES, INK_EDGE),
                linewidths=1,
                zorder=3,
            )
            _ = self.ax.add_collection(self._edge_lines)

        # Labels above the nodes
        label_font = FontProperties(size=LABEL_FONT_SIZE)
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
                facecolor=COLOR_INK,
                edgecolor=COLOR_INK,
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
            segments = self._pos[self._edge_idx]
            self._scatter._offsets3d = tuple(self._pos.T)
            self._edge_lines.set_segments(segments)
            self._edge_lines.set_geometry(segments)
            if self._halo is not None:
                self._halo._offsets3d = tuple(self._pos[self._accent_mask].T)
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
    ) -> tuple[Artist, ...]:
        """Return the node, edge, and label artists for animation blitting.

        Returns:
            A tuple containing the node scatter, edge lines, label collection,
            and optional halo collection.
        """
        artists: tuple[Artist, ...] = (
            self._scatter,
            self._edge_lines,
            self._label_collection,
        )
        if self._halo is not None:
            return (*artists, self._halo)
        return artists

    def set_alpha_scale(self, scale: npt.NDArray[np.float64]) -> None:
        """Apply a per-node alpha multiplier to nodes, halos and edges.

        Edge alpha uses the product of its two endpoint scales, so an edge fades
        out when either end does.

        Args:
            scale: (N,) array of multipliers in [0, 1], one per node.
        """
        if not self._is_3d:
            return

        # Path3DCollection has no _facecolor3d twin the way it has _sizes3d and
        # _linewidths3d; colours live in _facecolors and get depth-sorted on the
        # way out of get_facecolor, so these want plain node order.
        # Do not call set_alpha() on these collections: Collection._set_facecolor
        # feeds self._alpha to to_rgba_array, which overwrites the alpha column.
        colors = self._node_colors.copy()
        colors[:, 3] *= scale
        self._scatter.set_facecolor(colors)

        halo_colors = np.tile(
            to_rgba(COLOR_ACCENT, ACCENT_HALO), (self._accent_mask.sum(), 1)
        )
        halo_colors[:, 3] *= scale[self._accent_mask]
        self._halo.set_edgecolor(halo_colors)

        edge_scale = scale[self._edge_idx[:, 0]] * scale[self._edge_idx[:, 1]]
        self._edge_lines.set_alpha_scale(edge_scale)
        self._label_collection.set_alpha_scale(scale)
