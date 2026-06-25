from matplotlib.pylab import sin
import matplotlib.pyplot as plt
import math

fig, ax = plt.subplots()
x = [i * 2 * math.pi / 100 for i in range(100)]
line, = ax.plot(x, [math.sin(i) for i in x]) # Note the comma: ax.plot returns a list of Line2D objects

def update_line(new_y):
    # This is the high-performance way to update a plot
    line.set_ydata(new_y)
    fig.canvas.draw()
    fig.canvas.flush_events()

# Simulate a real-time update loop
i = 0
while True:
    updated_y = [sin(j + i/10.0) for j in x]
    update_line(updated_y)
    plt.pause(0.01)
    i += 1

