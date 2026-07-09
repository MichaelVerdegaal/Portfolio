from numpy._typing._array_like import NDArray

from numpy import float64

from numpy._core import dtype
import numpy.typing as npt
from typing import Any

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from collections.abc import Callable

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PathCollection

from src.graph import load_graph_data
from src.mpl_utils import create_figure

np.random.seed(2)

# Config
INTERVAL_MS = 10  # Animation interval in milliseconds
DURATION_SECONDS = 5  # Animation duration in seconds
FRAMES = DURATION_SECONDS * 1000 // INTERVAL_MS  # Number of frames in the animation
SAVE_PATH: str | None = None  # e.g. "animation.gif", None = show only

# Load data from YAML
graph_dict: dict[str, list[str]] = load_graph_data()


# Scene: owns the graph data and the matplotlib artists
class Graph:
    """
    Main class for managing graph data, including nodes, edges, and their coordinates.

    Coordinates are initialized randomly within the limits of XLIM & YLIM
    """

    def __init__(
        self,
        graph: dict[str, list[str]],
        axis_lim: tuple[int, int] = (0, 100),
        spawn_margin: int = 20,
    ):
        f"""
        Initialize graph based on dictionary

        args:
            graph: dictionary with graph data, adjacency list format
            axis_lim: tuple of axis limits used for plot creation and node spawning
            spawn_margin: subtracted from axis limits to nodes don't spawn on the edge
        """

        # Nodes
        self.node_names: list[str] = list(graph.keys())
        self.index: dict[str, int] = {name: i for i, name in enumerate(self.node_names)}

        # Edges
        self.edges: np.ndarray[tuple[int, ...]] = np.array(
            [
                (self.index[node_start], self.index[node_end])
                for node_start, neighbours in graph.items()
                for node_end in neighbours
            ],
            dtype=np.int32,
        )

        # Node coordinates
        self.coords: npt.NDArray[np.float64] = np.random.uniform(
            low=axis_lim[0] + spawn_margin,
            high=axis_lim[1] - spawn_margin,
            size=(len(self.node_names), 2),
        )

    @property
    def coords_x(self) -> npt.NDArray[np.float64]:
        return self.coords[:, 0]

    @property
    def coords_y(self) -> npt.NDArray[np.float64]:
        return self.coords[:, 1]

    @property
    def edges_start(self) -> npt.NDArray[np.int32]:
        return self.edges[:, 0]

    @property
    def edges_end(self) -> npt.NDArray[np.int32]:
        return self.edges[:, 1]

    @property
    def edge_lengths(self) -> npt.NDArray[np.float64]:
        d = self.coords[self.edges_end] - self.coords[self.edges_start]
        return np.hypot(d[:, 0], d[:, 1])


class GraphScene:
    def __init__(self, graph: Graph, fig: Figure, ax: Axes):
        self.graph: Graph = graph

        # Create nodes/edges with PathCollection and LineCollection
        self._scatter: PathCollection = ax.scatter(
            graph.coords_x, graph.coords_y, zorder=2
        )
        self._edge_lines: LineCollection = LineCollection(
            [], colors="black", linewidths=1, zorder=1
        )
        _ = ax.add_collection(self._edge_lines)
        self._edge_lines.set_segments(self.graph.coords[graph.edges])

    @property
    def coords(self) -> npt.NDArray[np.float64]:
        return self.graph.coords

    @coords.setter
    def coords(self, new_coords: npt.NDArray[np.float64]) -> None:
        self.graph.coords = new_coords
        self.move_nodes(new_coords)

    @property
    def coords_x(self) -> npt.NDArray[np.float64]:
        return self.graph.coords_x

    @property
    def coords_y(self) -> npt.NDArray[np.float64]:
        return self.graph.coords_y

    @property
    def edges(self) -> npt.NDArray[np.int32]:
        return self.graph.edges

    @property
    def edges_start(self) -> npt.NDArray[np.int32]:
        return self.graph.edges_start

    @property
    def edges_end(self) -> npt.NDArray[np.int32]:
        return self.graph.edges_end

    @property
    def edge_lengths(self) -> npt.NDArray[np.float64]:
        return self.graph.edge_lengths

    def move_nodes(self, new_coords: npt.ArrayLike) -> None:
        self._scatter.set_offsets(new_coords)
        self._edge_lines.set_segments(new_coords[self.edges])


# Main
fig, ax = create_figure()
G: Graph = Graph(graph_dict)
GScene: GraphScene = GraphScene(G, fig, ax)


# TODO

# target_len: NDArray[float64] = GScene.graph.edge_lengths
# # history = step_history(
# #     scene.coords,
# #     lambda pos: equalize_edges_step(pos, scene.edges, target_len),
# #     FRAMES,
# # )
# final_correction = equalize_edges_step(
#     GScene.graph.coords, GScene.graph.edges, target_len, step_size=1.0
# )
# final_layout = GScene.graph.coords + final_correction
# history = tween_history(GScene.graph.coords, final_layout, FRAMES)


def animate(frame: int):
    coords = GScene.coords

    # transform
    new_coords = coords + np.random.uniform(-1, 1, size=coords.shape) * 0.5

    # update scene
    GScene.coords = new_coords
    return GScene._scatter, GScene._edge_lines


anim = FuncAnimation(fig, animate, interval=INTERVAL_MS, frames=FRAMES, repeat=True)
fig.tight_layout()
plt.show()
