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

# More constants
INTERVAL = 200  # milliseconds
DURATION_SECONDS = 10  # seconds
DURATION = DURATION_SECONDS * 1000 // INTERVAL  # number of frames


# Calculate mean edge length once
MEAN_EDGE_LENGTH = np.mean([np.hypot(*(nodes_coords[b] - nodes_coords[a])) for a, b in edge_index])

def compute_layout(nodes, step_size=0.1):
    displacement = np.zeros_like(nodes)
    
    for a, b in edge_index:
        node_a = nodes[a]
        node_b = nodes[b]
        d = node_b - node_a
        dist = np.hypot(*d)
        
        correction = d / dist *  (dist - MEAN_EDGE_LENGTH) * step_size
        displacement[a] += correction
        displacement[b] -= correction

    return displacement


def animate(frame: int):
    # Get coordinates
    coordinates: np.ndarray = scatter.get_offsets()

    # Transform coordinates
    displacement = compute_layout(coordinates)
    new_coordinates = coordinates + displacement

    # Set new coordinates
    scatter.set_offsets(new_coordinates)
    edge_lines.set_segments(new_coordinates[edge_index])   
    return (scatter,)


# Show and save animation
anim = FuncAnimation(fig, animate, interval=INTERVAL, frames=DURATION, repeat=True)
fig.tight_layout()
anim.save(filename="animation.gif", writer="pillow")
plt.show()
