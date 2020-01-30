from __future__ import annotations
from collections import Counter
from typing import Iterator, Dict, Optional, Set, List, Iterable

import networkx as nx

from .utils.graph import (
    reroot_graph,
    topo_sort_edges,
    dfs_edges,
    path_to_root,
    topological_copy_slabs,
    find_slabs,
    find_branches_leaves,
)
from .utils.classes import TnId


class Tree:
    """Do not mutate"""

    def __init__(self, graph: nx.DiGraph, *, validate=True):
        self.graph: nx.DiGraph = graph

        self._strahler: Optional[Dict[TnId, int]] = None
        self._root: Optional[TnId] = None
        self._leaves: Optional[Set[TnId]] = None
        self._branches: Optional[Dict[TnId, int]] = None
        self._steps_from_root: Optional[Dict[TnId, int]] = None

        if validate:
            self._validate()

    @property
    def strahler(self) -> Dict[TnId, int]:
        if self._strahler is None:
            self._strahler = self._calculate_strahler()
        return self._strahler

    @property
    def root(self) -> TnId:
        if self._root is None:
            roots = [node for node, deg in self.graph.in_degree if deg == 0]
            if len(roots) != 1:
                raise ValueError(f"Found {len(roots)} possible roots")
            self._root = roots[0]

        return self._root

    @property
    def leaves(self) -> Set[TnId]:
        if self._leaves is None:
            self._branches, self._leaves = find_branches_leaves(self.graph)
        return self._leaves

    def _calculate_strahler(self) -> Dict[TnId, int]:
        strahler: Dict[TnId, int] = {}
        for node in nx.dfs_postorder_nodes(self.graph, self.root):
            succ = Counter(strahler[n] for n in self.graph.successors(node))

            if len(succ) == 0:
                strahler[node] = 1
                continue

            val, count = max(succ.items())
            if count > 1:
                val += 1
            strahler[node] = val

        return strahler

    def reroot(self, node) -> Tree:
        if node not in self.graph.nodes:
            raise ValueError("Node not in graph")

        out = self.copy()
        out.graph = reroot_graph(self.graph, node)
        return out

    @property
    def steps_from_root(self) -> Dict[TnId, int]:
        if self._steps_from_root is None:
            self._steps_from_root = {self.root: 0}
            for parent, child in topo_sort_edges(self.graph):
                self._steps_from_root[child] = self._steps_from_root[parent] + 1
        return self._steps_from_root

    @property
    def branches(self) -> Dict[TnId, int]:
        if self._branches is None:
            self._branches, self._leaves = find_branches_leaves(self.graph)
        return self._branches

    def _subcopy(self, node_set: Set[TnId]) -> Tree:
        new_g = self.graph.subgraph(node_set).copy()
        return type(self)(new_g)

    def copy(self) -> Tree:
        return self._subcopy(set(self.graph.nodes))

    def copy_below(self, node: TnId) -> Tree:
        node_set = {node}
        for _, child in dfs_edges(self.graph, node):
            node_set.add(child)

        return self._subcopy(node_set)

    def cut(self, *cuts: TnId) -> Iterator[Tree]:
        """
        For each treenode specified in ``cuts``, yields a tree rooted at that treenode,
        and terminating at either another cut, or a leaf.
        If the original root is not in ``cuts``, one additional tree will be yielded
        rooted at that original root.
        """
        cut_set = set(cuts)
        if self.root not in cuts:
            cuts = cuts + (self.root,)

        for cut in cuts:
            node_set = {cut}
            for _, child in dfs_edges(self.graph, cut, cut_set):
                node_set.add(child)

            yield self._subcopy(node_set)

    def _validate(self):
        if not nx.is_tree(self.graph):
            raise ValueError("Graph is not a tree")

    def slabs(self) -> Iterator[List[TnId]]:
        yield from find_slabs(self.graph, self.root, self.branches, self.leaves)

    @classmethod
    def empty(cls):
        return cls(nx.DiGraph())

    def prune_at(self, *nodes: TnId) -> Tree:
        if self.root in nodes:
            return type(self).empty()

        keep = {self.root}
        for _, child in dfs_edges(self.graph, self.root, nodes):
            keep.add(child)

        return self._subcopy(keep)

    def prune_branches_containing(self, nodes: Iterable[TnId]):
        branches = self.branches
        prune_at = set()
        for nb in nodes:
            this_n = nb
            for next_n in path_to_root(self.graph, nb):
                if next_n in branches and next_n != this_n:
                    prune_at.add(this_n)
                    break
                this_n = next_n
        return self.prune_at(*prune_at)

    def topological_copy(self):
        g, _ = topological_copy_slabs(self.slabs())
        return Tree(g)
