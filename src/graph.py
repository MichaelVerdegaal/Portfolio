import yaml


def load_graph_data() -> dict[str, list[str]]:
    """Load graph data from a YAML file."""
    with open("src/graph.yaml") as file:
        graph_yaml = yaml.safe_load(file)
    # Flatten into a single dict, empty list if no children
    graph = {}
    for node in graph_yaml:
        graph.update(node if isinstance(node, dict) else {node: []})
    return graph
