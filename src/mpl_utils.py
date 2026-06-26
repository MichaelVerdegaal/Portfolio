import matplotlib.pyplot as plt


def get_screen_size(DPI: int = 100) -> tuple[float, float]:
    """
    Get the screen size in inches.
    Returns:
        tuple: (screen_x_inches, screen_y_inches)
    """
    window = plt.get_current_fig_manager().window
    screen_x_pixels = window.winfo_screenwidth()
    screen_y_pixels = window.winfo_screenheight()
    screen_x_inches = screen_x_pixels / DPI
    screen_y_inches = screen_y_pixels / DPI
    return screen_x_inches, screen_y_inches
