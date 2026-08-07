from collections.abc import Callable, Iterable

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation

from src.animate import tween_history
from src.graphview import GraphView, load_graph_data
from src.layout import AXIS_MAX, AXIS_MIN, layout_function
from src.mpl_utils import create_figure, maximize_window

TARGET_FPS = 60
DURATION_SECONDS = 10
INTERVAL_MS = 1000 // TARGET_FPS
FRAMES = int(DURATION_SECONDS * TARGET_FPS)
IS_3D = True
SAVE_ANIM = False
FULLSCREEN = False
ELEVATION_ROTATIONS = 0.4
AZIMUTH_ROTATIONS = 0.4


# --- Main  ----------------------------------------------------------------------------
fig, ax = create_figure(is_3d=IS_3D)
graph_data: dict[str, Iterable[str]] = load_graph_data()
G = GraphView(
    fig,
    ax,
    nx.DiGraph(graph_data),
    axis_lim=(AXIS_MIN, AXIS_MAX),
    spawn_margin=10,
    is_3d=IS_3D,
)

start_layout = G.pos.copy()
final_layout = layout_function(G, IS_3D)
history = tween_history(start_layout, final_layout, FRAMES)


def animate(frame: int):
    """Main Matplotlib animation function

    Grabs a frame from the coordinate history for each frame.

    Args:
        frame: The current frame index into the position history.

    Returns:
        The node and edge artists for blitting.
    """
    G.pos = history[min(frame, len(history) - 1)]

    view_init: Callable[..., None] | None = getattr(ax, "view_init", None)
    if IS_3D and view_init is not None:
        progress = frame / max(FRAMES - 1, 1)
        view_init(
            elev=30 + 360 * ELEVATION_ROTATIONS * progress,
            azim=100 + 360 * AZIMUTH_ROTATIONS * progress,
        )

    return G.get_artists()


anim = FuncAnimation(
    fig,
    func=animate,
    interval=INTERVAL_MS,
    frames=FRAMES,
    repeat=False,
    blit=False if IS_3D else True,  # Limited support for Axes3D blitting
)
if SAVE_ANIM:
    anim.save("animation.mp4", writer="ffmpeg")
if FULLSCREEN:
    maximize_window(fig)
plt.show()
