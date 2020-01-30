from __future__ import annotations
from collections import defaultdict
from typing import Dict, Optional, Set, DefaultDict

import networkx as nx

from .tree import Tree

from .utils.graph import (
    topo_sort_edges,
    topological_copy_slabs,
    resample_slabs,
    unique_parent,
    leafward_slab,
)
from .utils.misc import subset_dict
from .utils.classes import TnId, CoordXYZ, EdgeData


class SpacedTree(Tree):
    def __init__(
        self,
        graph: nx.DiGraph,
        node_loc: Dict[TnId, CoordXYZ],
        node_radius: Dict[TnId, float],
        *,
        validate=True,
    ):
        self.node_loc = node_loc
        self.node_radius = node_radius

        self.is_topological_copy = False

        self._distance_from_root: Optional[Dict[TnId, float]] = None
        self._edge_length: Optional[EdgeData[float]] = None

        super().__init__(graph, validate=validate)

    @property
    def edge_length(self):
        if self._edge_length is None:
            data: EdgeData[float] = EdgeData()
            for (tn1, tn2), v in self.edge_confidence.items():
                data[(tn1, tn2)] = (self.node_loc[tn1] - self.node_loc[tn2]).norm()
            self._edge_length = data
        return self._edge_length

    @property
    def distance_from_root(self):
        if self._distance_from_root is None:
            self._distance_from_root = {self.root: 0}
            for parent, child in topo_sort_edges(self.graph):
                self._distance_from_root[child] = (
                    self._distance_from_root[parent] + self.edge_length[(parent, child)]
                )
        return self._distance_from_root

    def _subcopy(self, node_set: Set[TnId]) -> SpacedTree:
        graph = self.graph.subgraph(node_set).copy()
        locations = subset_dict(self.node_loc, node_set)
        radius = subset_dict(self.node_radius, node_set)
        return SpacedTree(graph, locations, radius)  # type: ignore

    def _validate(self):
        super()._validate()
        node_set = set(self.graph.nodes)
        if node_set != set(self.node_loc):
            raise ValueError("Node location keys do not match graph nodes")
        if not node_set.issuperset(self.node_radius):
            raise ValueError("Node radii are not subset of graph nodes")

    def resample(self, edge_length) -> SpacedTree:
        g, locations = resample_slabs(self.slabs(), self.node_loc, edge_length)
        radius: Dict[TnId, float] = subset_dict(
            self.node_radius, set(g.nodes)
        )  # type: ignore
        return SpacedTree(g, locations, radius, validate=False)

    @classmethod
    def from_tree(cls, tree: Tree, node_loc, node_radius, *, validate=True):
        return cls(tree.graph, node_loc, node_radius, validate=validate)

    def topological_copy(self):
        g, _ = topological_copy_slabs(self.slabs())
        dists = self.distance_from_root
        edge_length = EdgeData()
        for u, v in g.edges():
            edge_length[u, v] = dists[v] - dists[u]

        nodes = g.nodes()
        locations = subset_dict(self.node_loc, nodes)
        radius = subset_dict(self.node_loc, nodes)

        new = SpacedTree(g, locations, radius, validate=False)
        new._edge_length = edge_length
        new.is_topological_copy = True
        return new

    def length_below_branches(self) -> Dict[TnId, float]:
        out: DefaultDict[TnId, float] = defaultdict(lambda: 0)

        leaves = list(self.leaves)
        branches = dict(self.branches)
        edge_len = self.edge_length
        while leaves:
            prev_node = leaves.pop()
            prev_length = 0
            while True:
                current_node = unique_parent(self.graph, prev_node)
                if current_node is None:
                    break
                branch_count = branches.get(current_node)
                if branch_count is not None:
                    out[current_node] += prev_length + edge_len[prev_node, current_node]
                    if branch_count > 0:
                        branches[current_node] = branch_count - 1
                        break

        return dict(out)

    def get_significant_branches(self, n_branches: int) -> SpacedTree:
        keep_nodes = {self.root}
        branch_lens = self.length_below_branches()
        branches_to_keep = set(
            sorted(branch_lens, key=branch_lens.get, reverse=True)[:n_branches]
        )
        to_visit = [self.root]
        while to_visit:
            slab, children = leafward_slab(self.graph, to_visit.pop())
            keep_nodes.union(slab)
            if slab[-1] in branches_to_keep:
                to_visit.extend(children)
        return self._subcopy(keep_nodes)
