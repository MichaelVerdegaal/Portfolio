import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import random
from src.graph import load_graph_data
from matplotlib.patches import ConnectionPatch



# Pyplot settings
plt.rcParams['figure.figsize'] = [15, 7.5]

# Constants
NODES, EDGES = load_graph_data()
XLIM_MIN, XLIM_MAX = 0, 100
YLIM_MIN, YLIM_MAX = 0, 100


def create_plot():
    fig, ax = plt.subplots()
    ax.set_xlim(XLIM_MIN, XLIM_MAX)
    ax.set_ylim(YLIM_MIN, YLIM_MAX)

    # Create coordinates
    node_dict: dict = {}
    nodes_x, nodes_y = [], []
    for node in NODES:
        coord_x, coord_y = random.randint(XLIM_MIN + 10, XLIM_MAX - 10), random.randint(XLIM_MIN + 10, XLIM_MAX - 10)
        nodes_x.append(coord_x)
        nodes_y.append(coord_y)
        node_dict[node] = (coord_x, coord_y)

    # Draw nodes
    # matplotlib.collections.PathCollection
    nodePaths = ax.scatter(nodes_x, nodes_y)

    # Draw edges
    for edge in EDGES:
        node1, node2 = edge
        x1, y1 = node_dict[node1]
        x2, y2 = node_dict[node2]
        ax.add_patch(ConnectionPatch(xyA=(x1, y1),xyB=(x2, y2), coordsA=ax.transData, arrowstyle="-|>", color="black", linewidth=1))

    plt.tight_layout()
    return fig, ax