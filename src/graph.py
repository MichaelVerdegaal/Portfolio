from typing import NamedTuple

import numpy as np
import numpy.typing as npt
import yaml
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.figure import Figure

from src.mpl_utils import COLOR_EDGES, COLOR_NODES

# Set randomness
np.random.seed(3)


def load_graph_data() -> dict[str, list[str]]:
    """Load graph data in adjacency list format from a YAML file."""
    with open("src/graph.yaml") as file:
        graph_yaml = yaml.safe_load(file)
    # Flatten into a single dict, empty list if no children
    graph = {}
    for node in graph_yaml:
        graph.update(node if isinstance(node, dict) else {node: []})
    return graph


class Node(NamedTuple):
    name: str
    index_nbr: int
    x: float
    y: float
    children: list[str]


class Graph:
    """
    Main class for managing graph data, including nodes, edges, and their coordinates.

    Coordinates are initialized randomly within the limits of XLIM & YLIM
    """

    def __init__(
        self,
        fig: Figure,
        ax: Axes,
        graph: dict[str, list[str]],
        axis_lim: tuple[int, int] = (0, 100),
        spawn_margin: int = 20,
    ):
        """
        Initialize graph based on dictionary

        args:
            fig: Matplotlib figure object
            ax: Matplotlib axes object
            graph: dictionary with graph data, adjacency list format
            axis_lim: tuple of axis limits used for plot creation and node spawning
            spawn_margin: subtracted from axis limits to nodes don't spawn on the edge
        """
        # Nodes
        self._graph: dict[str, list[str]] = graph
        self.index: dict[str, int] = {name: i for i, name in enumerate(graph.keys())}

        # Edges
        self._edges: npt.NDArray[np.int32] = np.array(
            [
                (self.index[node_start], self.index[node_end])
                for node_start, neighbours in graph.items()
                for node_end in neighbours
            ],
            dtype=np.int32,
        )

        # Node coordinates
        self._coords: npt.NDArray[np.float64] = np.random.uniform(
            low=axis_lim[0] + spawn_margin,
            high=axis_lim[1] - spawn_margin,
            size=(len(self._graph), 2),
        )
        self._coords_original: npt.NDArray[np.float64] = self._coords.copy()

        # Matplotlib, Create nodes with PathCollection and edges with LineCollection
        self.fig: Figure = fig
        self.ax: Axes = ax

        self._scatter: PathCollection = ax.scatter(
            self.coords_x, self.coords_y, color=COLOR_NODES, zorder=2
        )
        self._edge_lines: LineCollection = LineCollection(
            [], color=COLOR_EDGES, linewidths=1, zorder=1
        )
        _ = ax.add_collection(self._edge_lines)
        self._edge_lines.set_segments(self.coords[self.edges])

    @property
    def coords(self) -> npt.NDArray[np.float64]:
        return self._coords

    @coords.setter
    def coords(self, new_coords: npt.NDArray[np.float64]) -> None:
        self._coords = new_coords
        self._scatter.set_offsets(new_coords)
        self._edge_lines.set_segments(new_coords[self.edges])

    @property
    def coords_x(self) -> npt.NDArray[np.float64]:
        return self.coords[:, 0]

    @property
    def coords_y(self) -> npt.NDArray[np.float64]:
        return self.coords[:, 1]

    @property
    def edges(self) -> npt.NDArray[np.int32]:
        return self._edges

    @property
    def edges_start(self) -> npt.NDArray[np.int32]:
        return self.edges[:, 0]

    @property
    def edges_end(self) -> npt.NDArray[np.int32]:
        return self.edges[:, 1]

    @property
    def edge_lengths(self) -> npt.NDArray[np.float64]:
        d: npt.NDArray[np.float64] = (
            self.coords[self.edges_end] - self.coords[self.edges_start]
        )
        return np.hypot(d[:, 0], d[:, 1])

    def get_artists(self) -> tuple[PathCollection, LineCollection]:
        return self._scatter, self._edge_lines

    def get_node_index(self, name: str) -> int | None:
        return self.index.get(name, None)

    def get_node_coords(self, name: str) -> npt.NDArray[np.float64] | None:
        """Return the X-Y coordinates of a node by name."""
        index = self.get_node_index(name)
        if index is not None:
            return self.coords[index]
        return None

    def get_children(self, name: str) -> list[str]:
        """Return the children of a node by name."""
        children = self._graph.get(name, None)
        return children if children is not None else []

    def get_node(self, name: str) -> Node | None:
        """Return a Node tuple with data by name."""
        index: int | None = self.get_node_index(name)
        if index is not None:
            node_coords: npt.NDArray[np.float64] = self.coords[index]
            children = self.get_children(name)
            return Node(
                name=name,
                index_nbr=index,
                x=float(node_coords[0]),
                y=float(node_coords[1]),
                children=children,
            )
        return None

    def move_node(self, name: str, new_coords: npt.ArrayLike) -> Node | None:
        """Move a single node to new coordinates and return the updated node."""
        new_coords = np.asarray(new_coords, dtype=np.float64)
        node_index: int | None = self.get_node_index(name)
        if node_index is None:
            return None
        updated_coords = self.coords.copy()
        updated_coords[node_index] = new_coords
        self.coords = updated_coords
        return self.get_node(name)
