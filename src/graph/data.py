"""YAML loading for the graph adjacency list."""

from collections.abc import Iterable

import yaml

from src.config import GRAPH_YAML


def load_graph_data() -> dict[str, Iterable[str]]:
    """Load an adjacency-list graph from YAML, preserving parent -> child direction.

    Each YAML entry is either a bare node name or a {name: [children]} mapping.

    Returns:
        A dictionary mapping each node name to an iterable of its child node names.
    """
    with GRAPH_YAML.open() as file:
        entries: list[str | dict[str, list[str]]] = yaml.safe_load(file)
    adjacency: dict[str, Iterable[str]] = {}
    for entry in entries:
        if isinstance(entry, dict):
            adjacency.update(entry)
        else:
            adjacency[entry] = []
    return adjacency
