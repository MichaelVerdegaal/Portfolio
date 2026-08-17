"""Shared scene composition used by the preview and export scripts."""

from collections.abc import Callable

import networkx as nx
import numpy as np
import numpy.typing as npt
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.axes3d import Axes3D

from . import config
from src.animation import Camera
from src.graph import load_graph_data
from src.render import create_figure, GraphView


def build_scene(
    figsize: tuple[float, float] | None = config.FIGSIZE,
    dpi: float | None = None,
    is_3d: bool = True,
) -> tuple[Figure, Axes | Axes3D, GraphView]:
    """Build the figure, axes and graph view.

    Camera framing and axis bounds come from create_figure, so the export
    and the interactive preview stay in sync.

    Args:
        figsize: Figure size in inches. Defaults to config.FIGSIZE.
        dpi: Resolution in dots per inch. Defaults to matplotlib rcParams.
        is_3d: Whether to create a 3D axes.

    Returns:
        The figure, its axes, and the GraphView holding node positions.
    """
    fig, ax = create_figure(figsize=figsize, dpi=dpi, is_3d=is_3d)
    view = GraphView(
        fig,
        ax,
        nx.DiGraph(load_graph_data()),
        axis_lim=(config.AXIS_MIN, config.AXIS_MAX),
        spawn_margin=config.SPAWN_MARGIN,
        is_3d=is_3d,
    )
    return fig, ax, view


def frame_updater(
    view: GraphView,
    ax: Axes | Axes3D,
    pos_for: Callable[[int], npt.NDArray[np.float64]],
    camera_for: Callable[[int], Camera] | None = None,
    alpha_for: Callable[[int], npt.NDArray[np.float64]] | None = None,
) -> Callable[[int], tuple[Artist, ...]]:
    """Return the closure passed to FuncAnimation.

    Args:
        view: The GraphView whose positions are updated per frame.
        ax: The axes whose camera is optionally driven.
        pos_for: Maps a frame index to an (N, 2|3) position array.
        camera_for: Optional map from frame index to (elev, azim, roll).
        alpha_for: Optional map from frame index to per-node alpha multipliers.

    Returns:
        A callback suitable for FuncAnimation.
    """

    def update(frame: int) -> tuple[Artist, ...]:
        view.pos = pos_for(frame)
        if alpha_for is not None:
            view.set_alpha_scale(alpha_for(frame))
        if camera_for is not None:
            elev, azim, roll = camera_for(frame)
            ax.view_init(elev=elev, azim=azim, roll=roll)
        return view.get_artists()

    return update
