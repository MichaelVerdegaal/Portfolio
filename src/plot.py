import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.patches import ConnectionPatch

from src.graph import load_graph_data
from src.mpl_utils import get_screen_size

# Screen info
screen_x_inches, screen_y_inches = get_screen_size(DPI=100)
fig_size = (screen_x_inches / 2, screen_y_inches / 2)

# Pyplot settings
plt.rcParams["figure.figsize"] = fig_size

# Constants
NODES, EDGES = load_graph_data()
XLIM_MIN, XLIM_MAX = 0, 100
YLIM_MIN, YLIM_MAX = 0, 100


def create_plot():
    fig, ax = plt.subplots()
    ax.set(xlim=(XLIM_MIN, XLIM_MAX), ylim=(YLIM_MIN, YLIM_MAX))

    # Create coordinates
    node_dict: dict = {}
    nodes_x, nodes_y = [], []
    for node in NODES:
        nodes_x = np.random.randint(XLIM_MIN + 10, XLIM_MAX - 10, size=len(NODES))
        nodes_y = np.random.randint(YLIM_MIN + 10, YLIM_MAX - 10, size=len(NODES))
        for i, node in enumerate(NODES):
            node_dict[node] = (nodes_x[i], nodes_y[i])

    # Draw nodes (returns list of Path objects)
    _: PathCollection = ax.scatter(nodes_x, nodes_y)

    # Draw edges
    for edge in EDGES:
        node1, node2 = edge
        x1, y1 = node_dict[node1]
        x2, y2 = node_dict[node2]
        ax.add_patch(
            ConnectionPatch(
                xyA=(x1, y1),
                xyB=(x2, y2),
                coordsA=ax.transData,
                arrowstyle="-|>",
                color="black",
                linewidth=1,
            )
        )

    plt.tight_layout()
    return fig, ax
