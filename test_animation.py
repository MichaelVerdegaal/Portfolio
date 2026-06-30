from matplotlib.patches import ConnectionPatch
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection, LineCollection
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.animation import FuncAnimation
from src.graph import load_graph_data
from src.mpl_utils import get_screen_size
import math

# Screen info
screen_x_inches, screen_y_inches = get_screen_size()
fig_size = (screen_x_inches / 2, screen_y_inches / 2)

# Pyplot settings
plt.rcParams["figure.figsize"] = fig_size

# Constants
GRAPH: dict[str, list[str]] = load_graph_data()
NODES: list[str] = list(GRAPH.keys())
XLIM_MIN, XLIM_MAX = 0, 100
YLIM_MIN, YLIM_MAX = 0, 100

# Create graph
fig, ax = plt.subplots()
ax.set(xlim=(XLIM_MIN, XLIM_MAX), ylim=(YLIM_MIN, YLIM_MAX))

# Create indices
node_index = {name: i for i , name in enumerate(NODES)}
edge_index = np.array(
    [(node_index[v], node_index[u]) for v, neighbors in GRAPH.items() for u in neighbors]
)

# Create coordinates
nodes_coords = np.random.uniform(low=XLIM_MIN + 20, high=XLIM_MAX - 20, size=(len(NODES), 2))

# Draw nodes
scatter: PathCollection = ax.scatter(nodes_coords[:, 0], nodes_coords[:, 1])

# Draw edges
edge_lines = LineCollection(nodes_coords[edge_index], colors="black", linewidths=1, zorder=1)
ax.add_collection(edge_lines)

    
AMPLITUDE = 5
phase = np.linspace(0, 2 * np.pi, len(NODES), endpoint=False).astype(np.float32)

def animate(frame: int):
    # Get coordinates
    coordinates: np.ndarray = scatter.get_offsets()

    # Transform coordinates
    coordinates[:, 1] += AMPLITUDE * np.sin(frame + phase)

    # Set new coordinates
    scatter.set_offsets(coordinates)
    edge_lines.set_segments(coordinates[edge_index])   
    return (scatter,)


# get first object of the PathCollection
first_path: Path = scatter.get_paths()[0]

anim = FuncAnimation(fig, animate, interval=200, frames=20, repeat=True)

fig.tight_layout()
# anim.save(filename="animation.gif", writer="pillow")
plt.show()
