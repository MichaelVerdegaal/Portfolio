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
from matplotlib.collections import LineCollection

from src.graph import load_graph_data
from src.mpl_utils import create_figure

np.random.seed(2)

# --- Config -----------------------------------------------------------------
XLIM = (0, 100)  # X-axis limits
YLIM = (0, 100)  # Y-axis limits
SPAWN_MARGIN = 20  # Margin for spawning nodes
INTERVAL_MS = 10  # Animation interval in milliseconds
DURATION_SECONDS = 5  # Animation duration in seconds
FRAMES = DURATION_SECONDS * 1000 // INTERVAL_MS  # Number of frames in the animation
SAVE_PATH: str | None = None  # e.g. "animation.gif", None = show only

# Load data from YAML
graph_dict: dict[str, list[str]] = load_graph_data()


# --- Scene: owns the graph data and the matplotlib artists -------------------
class Graph:
    """
    Main class for managing graph data, including nodes, edges, and their coordinates.

    Coordinates are initialized randomly within the limits of XLIM & YLIM
    """

    def __init__(
        self,
        graph: dict[str, list[str]],
        xlim: tuple[int, int] = (0, 100),
        ylim: tuple[int, int] = (0, 100),
    ):
        f"""Initialize graph based on dictionary

        args:
            graph: dictionary with graph data, adjecency list format ({"A": ["B"], "B": []})
            xlim: tuple of x-axis limits
            ylim: tuple of y-axis limits
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
            low=XLIM[0] + SPAWN_MARGIN,
            high=XLIM[1] - SPAWN_MARGIN,
            size=(len(self.node_names), 2),
        )

        """
        TODO: more methods/properties to access the right attributes?
        """


class GraphScene:
    def __init__(self, graph: Graph, fig: Figure, ax: Axes):
        self.graph: Graph = graph

        """
        TODO: create the scatter and Lines, and methods to set them
        """


# --- Main ----------------------------------------------------------------------
fig, ax = create_figure()
G: Graph = Graph(graph_dict)
