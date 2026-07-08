import matplotlib.pyplot as plt

from src.mpl_utils import create_figure

# create plot
fig, ax = create_figure()
ax.scatter([1, 2, 3], [5, 6, 7])

# Show plot
plt.show()
