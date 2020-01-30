from collections import defaultdict

import pytest
import networkx as nx

from arbor import Arbor, CoordXYZ, EdgeData


@pytest.fixture
def simple_arbor():
    """
        1
        |
        2
       / \
      3   5
     / \
    4   6
    """
    graph = nx.OrderedDiGraph()

    graph.add_edges_from([(1, 2), (2, 3), (3, 4), (2, 5), (3, 6)])
    nodes = sorted(graph.nodes)
    return Arbor(
        100,
        graph,
        {n: 1 for n in nodes},
        {n: CoordXYZ(n, 0, 0) for n in nodes},
        EdgeData({pair: 5 for pair in graph.edges}),
        dict(),
        defaultdict(list),
    )
