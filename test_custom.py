from __future__ import annotations

import contextlib
from collections.abc import Iterable
from typing import Any

import networkx as nx
import numpy as np
import numpy.typing as npt
import yaml
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.figure import Figure

from src.mpl_utils import COLOR_EDGES, COLOR_NODES, create_figure

NodeName = str
Position = npt.NDArray[np.float64]


class MPLGraph(nx.DiGraph):
    """DiGraph whose nodes carry a 2-D 'pos' attribute and that keeps a
    PathCollection (nodes) and LineCollection (edges) in sync with graph
    state.
    """

    POS_ATTR = "pos"

    def __init__(
        self,
        fig: Figure,
        ax: Axes,
        incoming_graph_data=None,
        *,
        pos: dict[NodeName, np.ndarray] | None = None,
        axis_lim: tuple[float, float] = (0.0, 100.0),
        spawn_margin: float = 20.0,
        rng: np.random.Generator | None = None,
        node_color: Any = COLOR_NODES,
        edge_color: Any = COLOR_EDGES,
        node_size: float = 60.0,
        edge_width: float = 1.0,
        **attr,
    ) -> None:
        self.fig = fig
        self.ax = ax
        self._rng = rng if rng is not None else np.random.default_rng()
        self._pos_low = axis_lim[0] + spawn_margin
        self._pos_high = axis_lim[1] - spawn_margin

        # Suppress redraws during __init__ so bulk population doesn't thrash.
        self._suspend_redraw = True

        self._nodes_pc: PathCollection = ax.scatter(
            [],
            [],
            s=node_size,
            color=node_color,
            zorder=2,
        )
        self._edges_lc: LineCollection = LineCollection(
            [],
            colors=edge_color,
            linewidths=edge_width,
            zorder=1,
        )
        ax.add_collection(self._edges_lc)

        super().__init__(incoming_graph_data=incoming_graph_data, **attr)

        if pos is not None:
            for n, p in pos.items():
                if n in self._node:
                    self._node[n][self.POS_ATTR] = np.asarray(p, dtype=float)

        self._assign_missing_positions()
        self._suspend_redraw = False
        self.redraw()

    # ---- position bookkeeping -------------------------------------------------

    def _new_pos(self) -> Position:
        return self._rng.uniform(self._pos_low, self._pos_high, size=2)

    def _assign_missing_positions(self) -> None:
        for data in self._node.values():
            if self.POS_ATTR not in data:
                data[self.POS_ATTR] = self._new_pos()

    def positions(self) -> npt.NDArray[np.float64]:
        """(N, 2) array of node positions in iteration order."""
        if not self._node:
            return np.zeros((0, 2), dtype=float)
        return np.array(
            [self._node[n][self.POS_ATTR] for n in self._node],
            dtype=float,
        )

    def edge_segments(self) -> npt.NDArray[np.float64]:
        """(E, 2, 2) array of edge endpoint coordinates."""
        if self.number_of_edges() == 0:
            return np.zeros((0, 2, 2), dtype=float)
        node = self._node
        p = self.POS_ATTR
        return np.array(
            [[node[u][p], node[v][p]] for u, v in self.edges],
            dtype=float,
        )

    def set_position(self, n: NodeName, xy) -> None:
        """Move node *n* to *xy* and redraw."""
        self._node[n][self.POS_ATTR] = np.asarray(xy, dtype=float)
        self.redraw()

    # ---- rendering ------------------------------------------------------------

    def redraw(self) -> None:
        """Rebuild scatter offsets and line segments from current graph state."""
        if self._suspend_redraw:
            return
        self._nodes_pc.set_offsets(self.positions())
        segs = self.edge_segments()
        self._edges_lc.set_segments(list(segs) if segs.size else [])
        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw_idle()

    @contextlib.contextmanager
    def batch_update(self):
        """Context manager that defers redraws until the block exits."""
        prev = self._suspend_redraw
        self._suspend_redraw = True
        try:
            yield self
        finally:
            self._suspend_redraw = prev
            self.redraw()

    # ---- graph mutations ------------------------------------------------------

    def add_node(self, node_for_adding, **attr):
        super().add_node(node_for_adding, **attr)
        data = self._node[node_for_adding]
        if self.POS_ATTR not in data:
            data[self.POS_ATTR] = self._new_pos()
        self.redraw()

    def add_nodes_from(self, nodes_for_adding, **attr):
        super().add_nodes_from(nodes_for_adding, **attr)
        self._assign_missing_positions()
        self.redraw()

    def remove_node(self, n):
        super().remove_node(n)
        self.redraw()

    def remove_nodes_from(self, nodes):
        super().remove_nodes_from(nodes)
        self.redraw()

    def add_edge(self, u_of_edge, v_of_edge, **attr):
        super().add_edge(u_of_edge, v_of_edge, **attr)
        # add_edge auto-creates missing endpoints; give them a position.
        self._assign_missing_positions()
        self.redraw()

    def add_edges_from(self, ebunch_to_add, **attr):
        super().add_edges_from(ebunch_to_add, **attr)
        self._assign_missing_positions()
        self.redraw()

    def remove_edge(self, u, v):
        super().remove_edge(u, v)
        self.redraw()

    def remove_edges_from(self, ebunch):
        super().remove_edges_from(ebunch)
        self.redraw()

    def clear(self):
        super().clear()
        self.redraw()

    def clear_edges(self):
        super().clear_edges()
        self.redraw()


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
G = MPLGraph(fig=fig, ax=ax, incoming_graph_data=graph_data)

plt.show()
