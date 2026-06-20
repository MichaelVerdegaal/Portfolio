import matplotlib.pyplot as plt
from pyscript import display, when


def create_graph() -> tuple[plt.figure.Figure, plt.axes.Axes]:
    x = [1, 2, 3, 4, 5]
    y = [2, 3, 5, 7, 11]

    # plot
    fig, ax = plt.subplots()
    ax.scatter(x, y)
    return fig, ax


@when("click", "#clickMe")
def handler():
    fig, _ = create_graph()

    # Displays plot as image.
    display(fig)
    plt.close(fig)


