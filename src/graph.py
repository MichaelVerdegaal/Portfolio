import yaml

def load_graph_data() -> dict:
    with open("src/skills.yaml", "r") as file:
        tree = yaml.safe_load(file)

    nodes = [n for n in tree["tree"]]
    print(nodes)
    
    return nodes

load_graph_data()