import matplotlib.pyplot as plt
from pyscript import display, when

from .plot import create_plot


@when("click", "#clickMe")
def handler():
    fig, _ = create_plot()

    # Displays plot as image.
    display(fig)
    plt.close(fig)
