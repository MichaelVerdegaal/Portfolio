from matplotlib.animation import FuncAnimation
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection
from src.mpl_utils import get_screen_size
from src.graph import load_graph_data

# Screen info
screen_x_inches, screen_y_inches = get_screen_size(DPI=100)
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
    scatter.set_offsets(
        np.column_stack((np.random.randint(XLIM_MIN + frame, XLIM_MAX -  frame, size=len(NODES)),
                         np.random.randint(YLIM_MIN + frame, YLIM_MAX -  frame, size=len(NODES))))
    )
    return (scatter,)


plt.tight_layout()
# anim = FuncAnimation(fig, animate, interval=100, frames=len(NODES)-1, repeat=True)

plt.show()