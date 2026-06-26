import yaml


def load_graph_data() -> tuple[list, list]:
    with open("src/tree.yaml", "r") as file:
        tree = yaml.safe_load(file)

    nodes = [n for n in tree["nodes"]]
    edges = [e for e in tree["edges"]]

    return nodes, edges
