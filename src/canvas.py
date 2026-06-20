from pyscript import when, display
# import matplotlib.pyplot as plt

# def create_graph():
#     # sample data
#     x = [1, 2, 3, 4, 5]
#     y = [2, 3, 5, 7, 11]

#     # plot
#     fig, ax = plt.subplots()
#     ax.scatter(x, y, vmin=0, vmax=100)
#     ax.set(xlim=(0, 8), xticks=range(0, 9), ylim=(0, 8), yticks =range(0, 9))
#     plt.show()

@when("click", "#clickMe")
def handler():
    # create_graph()
    display("Button clicked!")