from matplotlib.patches import ConnectionPatch
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.animation import FuncAnimation
from src.graph import load_graph_data
from src.mpl_utils import get_screen_size

# Screen info
screen_x_inches, screen_y_inches = get_screen_size()
fig_size = (screen_x_inches / 2, screen_y_inches / 2)

# Pyplot settings
plt.rcParams["figure.figsize"] = fig_size

# Constants
NODES, EDGES = load_graph_data()
XLIM_MIN, XLIM_MAX = 0, 100
YLIM_MIN, YLIM_MAX = 0, 100


fig, ax = plt.subplots()
ax.set(xlim=(XLIM_MIN, XLIM_MAX), ylim=(YLIM_MIN, YLIM_MAX))

# Create coordinates
nodes_x = np.random.randint(XLIM_MIN + 10, XLIM_MAX - 10, size=len(NODES))
nodes_y = np.random.randint(YLIM_MIN + 10, YLIM_MAX - 10, size=len(NODES))
node_dict = {}
for i, node in enumerate(NODES):
    node_dict[node] = (nodes_x[i], nodes_y[i])

# Draw nodes
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
    

def animate(frame: int):
    coordinates = scatter.get_offsets()
    np_coordinates = np.array(coordinates)
    scatter.set_offsets(np_coordinates.tolist())
    return (scatter,)


# get first object of the PathCollection
first_path: Path = scatter.get_paths()[0]

anim = FuncAnimation(fig, animate, interval=100, frames=50, repeat=True)

fig.tight_layout()
# anim.save(filename="animation.gif", writer="pillow")
plt.show()
