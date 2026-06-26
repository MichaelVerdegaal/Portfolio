import ctypes
import sys
import tkinter


def get_screen_size(dpi: int = 100) -> tuple[float, float]:
    """Get the primary screen size in inches.

    Args:
        dpi: Pixels per inch used to convert physical pixels to inches.

    Returns:
        Screen width and height in inches.
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

    return width_px / dpi, height_px / dpi