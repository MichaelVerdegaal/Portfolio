from collections.abc import Callable

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from matplotlib.animation import FuncAnimation
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.figure import Figure

from src.graph import load_graph_data
from src.mpl_utils import create_figure

np.random.seed(3)

# Config styling
COLOR_NODES: str = "#ff8f40"
COLOR_EDGES: str = "#bbb9b2"
COLOR_BG: str = "#101010"

# Config animation
TARGET_FPS = 60
DURATION_SECONDS: int = 5  # Animation duration in seconds
INTERVAL_MS: int  = 1000 // TARGET_FPS  # Animation interval in milliseconds
FRAMES = int(DURATION_SECONDS * TARGET_FPS)  # Total number of frames in the animation
SAVE_PATH: str | None = "animation.gif"  # e.g. "animation.gif", None = show only
print(f"{TARGET_FPS=}, {DURATION_SECONDS=}, {INTERVAL_MS=}, {FRAMES=}")

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
        """
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

    def get_node_index(self, name: str) -> int | None:
        return self.index.get(name, None)


class GraphScene:
    def __init__(self, graph: Graph, fig: Figure, ax: Axes):
        self.graph: Graph = graph

        # Create nodes/edges with PathCollection and LineCollection
        self._scatter: PathCollection = ax.scatter(
            graph.coords_x, graph.coords_y, color=COLOR_NODES, zorder=2
        )
        self._edge_lines: LineCollection = LineCollection(
            [], color=COLOR_EDGES, linewidths=1, zorder=1
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


# --- History builders: every mode ends as a (frames, N, 2) array ---------------
def ease_bezier(t: float) -> float:
    """Cubic bezier easing function for smooth transition"""
    return t * t * (3 - 2 * t)


def tween_history(
    start: np.ndarray,
    target: np.ndarray,
    frames: int,
    ease: Callable[[float], float] = ease_bezier,
) -> np.ndarray:
    """One-shot: interpolate from start to a precomputed target layout."""
    t = np.array([ease(i / (frames - 1)) for i in range(frames)])
    return start + (target - start) * t[:, None, None]


def step_history(
    start: np.ndarray,
    step_fn: Callable[[np.ndarray], np.ndarray],
    frames: int,
) -> np.ndarray:
    """Iterative: step_fn returns a displacement, applied cumulatively."""
    history = np.empty((frames, *start.shape))
    pos = start.copy()
    for i in range(frames):
        history[i] = pos
        pos = pos + step_fn(pos)
    return history

# --- Layout --------------------------------------------------------------------



# --- Main ----------------------------------------------------------------------
fig, ax = create_figure(bg_color=COLOR_BG)
G: Graph = Graph(graph_dict)
GScene: GraphScene = GraphScene(G, fig, ax)

target_len: np.float64 = GScene.edge_lengths.mean()
final_layout: npt.NDArray[np.float64] = np.random.uniform(
    low=0, high=80, size=(len(GScene.graph.node_names), 2)
)
history = tween_history(GScene.coords, final_layout, FRAMES)


def animate(frame: int):
    # coords = GScene.coords

    # transform
    new_coords = history[frame]

    # update scene
    GScene.coords = new_coords
    return GScene._scatter, GScene._edge_lines


anim = FuncAnimation(fig, func=animate, interval=INTERVAL_MS, frames=FRAMES, repeat=True)
fig.tight_layout()
if SAVE_PATH:
    anim.save(SAVE_PATH, writer="pillow", fps=TARGET_FPS)
plt.show()
