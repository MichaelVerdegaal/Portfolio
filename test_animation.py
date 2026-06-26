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

scatter: PathCollection = ax.scatter(nodes_x, nodes_y)


def animate(frame: int):
    coordinates = scatter.get_offsets()
    np_coordinates = np.array(coordinates)
    np_coordinates = np.roll(np_coordinates, -1, axis=0)
    # slightly move last item to create a smooth transition
    np_coordinates[-1] += np.random.uniform(-1, 1, size=2)
    scatter.set_offsets(np_coordinates.tolist())
    return (scatter,)


# get first object of the PathCollection
first_path: Path = scatter.get_paths()[0]

anim = FuncAnimation(fig, animate, interval=100, frames=3000, repeat=True)

fig.tight_layout()
anim.save(filename="animation.gif", writer="pillow")
plt.show()
