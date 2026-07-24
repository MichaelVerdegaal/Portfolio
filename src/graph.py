import networkx as nx


def count_crossings(above: list[int], below: list[int], graph: nx.DiGraph) -> int:
    """Count edge crossings between two adjacent layers.

    Two edges (u1, v1) and (u2, v2) cross when their endpoints are in
    opposite order in the two layers.

    Args:
        above: Node ids of the upper layer, in left-to-right order.
        below: Node ids of the lower layer, in left-to-right order.
        graph: The directed graph containing the edges.

    Returns:
        The number of crossing edge pairs between the two layers.
    """
    ix_above = {n: i for i, n in enumerate(above)}
    ix_below = {n: i for i, n in enumerate(below)}
    edges = [
        (ix_above[u], ix_below[v])
        for u in above
        for v in graph.successors(u)
        if v in ix_below
    ]
    return sum(
        1
        for i, (u1, v1) in enumerate(edges)
        for u2, v2 in edges[i + 1 :]
        if (u1 - u2) * (v1 - v2) < 0
    )


def total_crossings(layers: list[list[int]], graph: nx.DiGraph) -> int:
    """Sum edge crossings over all adjacent layer pairs.

    Args:
        layers: Layer orderings, top to bottom.
        graph: The directed graph containing the edges.

    Returns:
        The total crossing count for the whole layout.
    """
    return sum(
        count_crossings(layers[i], layers[i + 1], graph) for i in range(len(layers) - 1)
    )
