"""Interactive preview of the 3D graph animation."""

from collections.abc import Callable

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation

from src import config
from src.animate import tween_history
from src.graphview import GraphView, load_graph_data
from src.layout import layout_function
from src.mpl_utils import create_figure, maximize_window

IS_3D = True
SAVE_ANIM = False
FULLSCREEN = False
ELEVATION_ROTATIONS = 0.4
AZIMUTH_ROTATIONS = 0.4
INTERVAL_MS = 1000 // config.PREVIEW_FPS
FRAMES = config.PREVIEW_FPS * config.PREVIEW_SECONDS


def main() -> None:
    """Run the preview window with the layout convergence animation."""
    fig, ax = create_figure(figsize=config.FIGSIZE, is_3d=IS_3D)
    graph = GraphView(
        fig,
        ax,
        nx.DiGraph(load_graph_data()),
        axis_lim=(config.AXIS_MIN, config.AXIS_MAX),
        spawn_margin=config.SPAWN_MARGIN,
        is_3d=IS_3D,
    )

    history = tween_history(graph.pos.copy(), layout_function(graph, IS_3D), FRAMES)

    def animate(frame: int) -> tuple:
        """Grab a frame from the coordinate history and move the camera.

        Args:
            frame: The current frame index into the position history.

        Returns:
            The node, edge and label artists for blitting.
        """
        graph.pos = history[min(frame, len(history) - 1)]

        view_init: Callable[..., None] | None = getattr(ax, "view_init", None)
        if IS_3D and view_init is not None:
            progress = frame / max(FRAMES - 1, 1)
            view_init(
                elev=config.ELEV0 + 360 * ELEVATION_ROTATIONS * progress,
                azim=config.AZIM0 + 360 * AZIMUTH_ROTATIONS * progress,
            )

        return graph.get_artists()

    # anim must stay referenced or it is garbage collected and nothing draws.
    anim = FuncAnimation(
        fig,
        func=animate,
        interval=INTERVAL_MS,
        frames=FRAMES,
        repeat=False,
        blit=not IS_3D,  # Limited support for Axes3D blitting.
    )
    if SAVE_ANIM:
        anim.save("animation.mp4", writer="ffmpeg")
    if FULLSCREEN:
        maximize_window(fig)
    plt.show()


if __name__ == "__main__":
    main()
