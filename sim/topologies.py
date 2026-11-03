"""Topology generators matching the paper's T1/T2/T3 trial designs, plus a
scalable generator for the device-count sweep."""
from __future__ import annotations

import itertools


def line(n: int = 3) -> dict:
    """T1: a line of n devices, each only in range of its immediate neighbours.
    n=3 reproduces A-B-C (B relays between the two edge devices)."""
    nodes = [f"d{i}" for i in range(n)]
    graph = {node: [] for node in nodes}
    for a, b in zip(nodes, nodes[1:]):
        graph[a].append(b)
        graph[b].append(a)
    return graph


def clique(n: int = 5) -> dict:
    """T2: n devices all within range of each other (~5m)."""
    nodes = [f"d{i}" for i in range(n)]
    graph = {node: [] for node in nodes}
    for a, b in itertools.combinations(nodes, 2):
        graph[a].append(b)
        graph[b].append(a)
    return graph


def bridged_cliques(n: int = 5, cliques: int = 2) -> dict:
    """T3: `cliques` cliques of roughly equal size, joined in a chain by a
    single bridge device shared between each adjacent pair of cliques."""
    nodes_per_clique = max(2, n // cliques)
    graph: dict[str, list[str]] = {}
    clique_node_lists = []
    counter = itertools.count()
    for c in range(cliques):
        clique_nodes = [f"d{next(counter)}" for _ in range(nodes_per_clique)]
        for node in clique_nodes:
            graph[node] = []
        for a, b in itertools.combinations(clique_nodes, 2):
            graph[a].append(b)
            graph[b].append(a)
        clique_node_lists.append(clique_nodes)

    # bridge: reuse last node of clique i as first node of clique i+1
    for i in range(len(clique_node_lists) - 1):
        bridge_a = clique_node_lists[i][-1]
        bridge_b = clique_node_lists[i + 1][0]
        graph[bridge_a].append(bridge_b)
        graph[bridge_b].append(bridge_a)

    return graph


def scaled_room(n: int) -> dict:
    """Scale-sweep topology: same shape as T3 (bridged cliques), but the
    clique size and number of cliques both grow with n, roughly like a
    building with more rooms as the device count grows.
    Used for 'how do these metrics change as device count increases'."""
    cliques = max(1, round(n ** 0.5))
    return bridged_cliques(n=n, cliques=cliques)


TOPOLOGIES = {
    "T1_line": lambda: line(n=3),
    "T2_clique": lambda: clique(n=5),
    "T3_room_scale": lambda: bridged_cliques(n=5, cliques=2),
}
