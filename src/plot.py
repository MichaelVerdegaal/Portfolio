import random
from matplotlib.animation import FuncAnimation

import matplotlib.pyplot as plt
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
        coord_x, coord_y = (
            random.randint(XLIM_MIN + 10, XLIM_MAX - 10),
            random.randint(XLIM_MIN + 10, XLIM_MAX - 10),
        )
        nodes_x.append(coord_x)
        nodes_y.append(coord_y)
        node_dict[node] = (coord_x, coord_y)

    # Draw nodes (returns list of Path objects)
    scatter: PathCollection = ax.scatter(nodes_x, nodes_y)

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

    def animate(frame):
        scatter.set_offsets(
            [(random.randint(XLIM_MIN + 10, XLIM_MAX - 10), random.randint(YLIM_MIN + 10, YLIM_MAX - 10)) for _ in NODES]
        )
        return (scatter,)


    plt.tight_layout()
    anim = FuncAnimation(fig, animate, interval=100, frames=len(NODES)-1, repeat=True)
    return fig, ax, anim
