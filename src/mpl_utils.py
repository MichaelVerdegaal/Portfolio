import ctypes
import sys
import tkinter

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.projections import register_projection
from matplotlib.transforms import Bbox
from mpl_toolkits.mplot3d.axes3d import Axes3D

# Color constants
COLOR_BG: str = "#101010"
COLOR_NODES: str = "#ff8f40"
COLOR_EDGES: str = "#bbb9b2"

# Matplotlib config
mpl.rcParams["toolbar"] = "none"
mpl.rcParams["keymap.fullscreen"] = ["f", "escape"]
mpl.rcParams["axes3d.automargin"] = False


class WideAxes3D(Axes3D):
    """Axes3D that keeps its full rectangle instead of shrinking to a square.

    Axes3D.apply_aspect re-fits the axes to a square on every draw, which
    letterboxes the scene in a widescreen figure.
    """

    name = "wide3d"

    def apply_aspect(self, position: Bbox | None = None) -> None:
        if position is None:
            position = self.get_position(original=True)
        self._set_position(position, "active")


register_projection(WideAxes3D)


def maximize_window(fig: Figure, fullscreen: bool = True) -> None:
    """Maximise or fullscreen the figure window.

    Args:
        fig: Figure whose window to resize.
        fullscreen: If True, go borderless fullscreen; otherwise maximise.
    """
    manager = fig.canvas.manager
    if manager is None:
        raise RuntimeError(f"backend {plt.get_backend()!r} has no figure manager")

    if fullscreen:
        manager.full_screen_toggle()
        return

    backend = plt.get_backend().lower()
    if "qt" in backend:
        manager.window.showMaximized()
    elif "tk" in backend:
        manager.window.state("zoomed")
    else:
        return None


def centered_rect(
    fig: Figure, target_aspect: float
) -> tuple[float, float, float, float]:
    """Compute a centred axes rect with the given width/height ratio.

    Args:
        fig: Figure the axes will be added to.
        target_aspect: Desired axes width / height. Values below the figure's
            own aspect leave unused strips on the left and right.

    Returns:
        An (left, bottom, width, height) rect in figure coordinates.
    """
    fig_w, fig_h = fig.get_size_inches()
    fig_aspect = fig_w / fig_h
    if target_aspect < fig_aspect:
        width = target_aspect / fig_aspect
        return ((1.0 - width) / 2.0, 0.0, width, 1.0)
    height = fig_aspect / target_aspect
    return (0.0, (1.0 - height) / 2.0, 1.0, height)


def get_screen_size() -> tuple[float, float]:
    """Get the primary screen size in inches.

    Returns:
        Screen width and height in pixels.
    """

    if sys.platform == "win32":
        user32 = ctypes.windll.user32
        user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]

        # -4 = DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2. Scope it to this
        # thread and restore after, so the process stays DPI-unaware.
        previous = user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        try:
            width_px = user32.GetSystemMetrics(0)
            height_px = user32.GetSystemMetrics(1)
        finally:
            user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(previous))
    else:
        root = tkinter.Tk()
        root.withdraw()
        width_px = root.winfo_screenwidth()
        height_px = root.winfo_screenheight()
        root.destroy()

    return width_px, height_px


def create_figure_2d(
    figsize: tuple[float, float] | None = None,
    xlim: tuple[float, float] = (0, 100),
    ylim: tuple[float, float] = (0, 100),
    bg_color: str | None = COLOR_BG,
) -> tuple[Figure, Axes]:
    """Create a 2D matplotlib figure and axes with specified limits.

    Args:
        figsize: Optional tuple specifying the figure size in inches.
        xlim: Tuple specifying the x-axis limits.
        ylim: Tuple specifying the y-axis limits.
        bg_color: Background color for the figure and axes.

    Returns:
        A tuple containing the created Figure and Axes objects.
    """
    if figsize is None:
        screen_x_pixels, screen_y_pixels = get_screen_size()
        figsize = (screen_x_pixels / 100, screen_y_pixels / 100)

    fig, ax = plt.subplots(figsize=figsize)
    ax.set(xlim=xlim, ylim=ylim)
    ax.axis("off")

    if bg_color is not None:
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

    return fig, ax


def create_figure_3d(
    figsize: tuple[float, float] | None = None,
    xlim: tuple[float, float] = (0, 100),
    ylim: tuple[float, float] = (0, 100),
    zlim: tuple[float, float] = (0, 100),
    bg_color: str | None = COLOR_BG,
) -> tuple[Figure, Axes3D]:
    """Create a matplotlib figure with a 3D axes and specified limits.

    Args:
        figsize: Optional tuple specifying the figure size in inches.
        xlim: Tuple specifying the x-axis limits.
        ylim: Tuple specifying the y-axis limits.
        zlim: Tuple specifying the z-axis limits.
        bg_color: Background color for the figure and axes.

    Returns:
        A tuple containing the created Figure and Axes3D objects.
    """
    aspect_ratio = 16 / 9
    if figsize is None:
        screen_x_pixels, screen_y_pixels = get_screen_size()
        aspect_ratio = screen_x_pixels / screen_y_pixels
        figsize = (screen_x_pixels / 100, screen_y_pixels / 100)

    fig = plt.figure(figsize=figsize)
    ax: Axes3D = fig.add_axes(
        centered_rect(fig, aspect_ratio), projection="wide3d", computed_zorder=False
    )
    ax.set(xlim=xlim, ylim=ylim, zlim=zlim)
    ax.set_xlim3d(0, 100, view_margin=0)
    ax.set_box_aspect((1, 1, 1))
    ax.set_proj_type("persp", focal_length=0.1)
    ax.view_init(elev=30, azim=100)

    if bg_color is not None:
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

    ax.set_axis_off()
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_pane_color((0.0, 0.0, 0.0, 0.0))

    return fig, ax


def create_figure(
    figsize: tuple[float, float] | None = None,
    xlim: tuple[float, float] = (0, 100),
    ylim: tuple[float, float] = (0, 100),
    zlim: tuple[float, float] = (0, 100),
    bg_color: str | None = COLOR_BG,
    is_3d: bool = False,
) -> tuple[Figure, Axes | Axes3D]:
    """Create a matplotlib figure and axes with specified limits.

    Dispatches to ``create_figure_2d`` or ``create_figure_3d`` based on
    *is_3d*.

    Args:
        figsize: Optional tuple specifying the figure size in inches.
        xlim: Tuple specifying the x-axis limits.
        ylim: Tuple specifying the y-axis limits.
        zlim: Tuple specifying the z-axis limits (3D only).
        bg_color: Background color for the figure and axes.
        is_3d: If True, create a 3D axes; otherwise, create a 2D axes.
        disable_axis: Whether to hide axis decorations (3D only).

    Returns:
        A tuple containing the created Figure and Axes objects.
    """
    if is_3d:
        return create_figure_3d(
            figsize=figsize,
            xlim=xlim,
            ylim=ylim,
            zlim=zlim,
            bg_color=bg_color,
        )
    return create_figure_2d(
        figsize=figsize,
        xlim=xlim,
        ylim=ylim,
        bg_color=bg_color,
    )
