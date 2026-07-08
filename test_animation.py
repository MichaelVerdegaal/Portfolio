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


# --- Scene: owns the graph data and the matplotlib artists -------------------
class GraphScene:
    """Wraps node coords, edge index, and the two artists behind one draw()."""

    def __init__(self, graph: dict[str, list[str]], ax: Axes):
        self.names = list(graph.keys())
        index = {name: i for i, name in enumerate(self.names)}
        self.edges = np.array(
            [(index[v], index[u]) for v, nbrs in graph.items() for u in nbrs]
        )
        self.coords = np.random.uniform(
            low=XLIM[0] + SPAWN_MARGIN,
            high=XLIM[1] - SPAWN_MARGIN,
            size=(len(self.names), 2),
        )
        self._edge_lines = LineCollection([], colors="black", linewidths=1, zorder=1)
        ax.add_collection(self._edge_lines)
        self._scatter = ax.scatter(self.coords[:, 0], self.coords[:, 1], zorder=2)
        self.draw(self.coords)

    def draw(self, coords: np.ndarray) -> None:
        self._scatter.set_offsets(coords)
        self._edge_lines.set_segments(coords[self.edges])

    def edge_lengths(self, coords: np.ndarray) -> np.ndarray:
        d = coords[self.edges[:, 1]] - coords[self.edges[:, 0]]
        return np.hypot(d[:, 0], d[:, 1])

    @property
    def artists(self) -> tuple:
        return self._scatter, self._edge_lines


# --- Layout functions ---------------------------------------------------------
def equalize_edges_step(
    coords: np.ndarray,
    edges: np.ndarray,
    target_len: float,
    step_size: float = 0.05,
) -> np.ndarray:
    """One relaxation step pulling every edge toward target_len.

    Returns:
        Displacement array, same shape as coords.
    """
    disp = np.zeros_like(coords)
    for a, b in edges:
        d = coords[b] - coords[a]
        dist = np.hypot(*d)
        correction = d / dist * (dist - target_len) * step_size
        disp[a] += correction
        disp[b] -= correction
    return disp


# --- History builders: every mode ends as a (frames, N, 2) array ---------------
def ease_cubic(t: float) -> float:
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def tween_history(
    start: np.ndarray,
    target: np.ndarray,
    frames: int,
    ease: Callable[[float], float] = ease_cubic,
) -> np.ndarray:
    """One-shot: interpolate from start to a precomputed target layout."""
    t = np.array([ease(i / (frames - 1)) for i in range(frames)])
    return start + (target - start) * t[:, None, None]


def settle_history(
    start: np.ndarray,
    layout_fn: Callable[[np.ndarray], np.ndarray],
    frames: int,
    step_size: float = 0.1,
) -> np.ndarray:
    """One-shot made iterative: recompute the layout each frame, move a
    fraction toward it instead of jumping."""
    history = np.empty((frames, *start.shape))
    pos = start.copy()
    for i in range(frames):
        history[i] = pos
        pos = pos + (layout_fn(pos) - pos) * step_size
    return history


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


# --- Main ----------------------------------------------------------------------
fig, ax = create_figure()
scene = GraphScene(load_graph_data(), ax)

target_len = scene.edge_lengths(scene.coords).mean()
# history = step_history(
#     scene.coords,
#     lambda pos: equalize_edges_step(pos, scene.edges, target_len),
#     FRAMES,
# )
final_correction = equalize_edges_step(
    scene.coords, scene.edges, target_len, step_size=1.0
)
final_layout = scene.coords + final_correction
history = tween_history(scene.coords, final_layout, FRAMES)


def animate(frame: int):
    scene.draw(history[frame])
    return scene.artists


anim = FuncAnimation(fig, animate, interval=INTERVAL_MS, frames=FRAMES, repeat=True)
fig.tight_layout()
if SAVE_PATH:
    anim.save(SAVE_PATH, writer="pillow")
plt.show()
