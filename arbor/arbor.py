from __future__ import annotations
from typing import Set, Optional, Iterator, Dict, DefaultDict, List
import itertools
from collections import defaultdict

import networkx as nx

from .spaced_tree import SpacedTree
from .utils.classes import EdgeData, TnId, SkId, CoordXYZ, TreenodeConnector
from .utils.misc import subset_dict, path_edge_data
from .utils.graph import dfs_edges, topological_copy_slabs


class Arbor(SpacedTree):
    SOMA = "soma"
    NOT_A_BRANCH = "not a branch"
    AXON_SPLIT = "mw axon split"
    ENDS = "ends"

    def __init__(
        self,
        skid: SkId,
        graph: nx.DiGraph,
        node_loc: Dict[TnId, CoordXYZ],
        node_radius: Dict[TnId, float],
        edge_confidence: EdgeData[int],
        connectors: Dict[TnId, List[TreenodeConnector]],
        tags: DefaultDict[str, List[TnId]],
        *,
        validate=True,
    ):
        self.id = skid
        self.edge_confidence = edge_confidence
        self.connectors = connectors
        self.tags = tags

        super().__init__(graph, node_loc, node_radius, validate=validate)

    def _validate(self):
        super()._validate()
        faux_edata = EdgeData((k, None) for k in self.graph.edges)
        if faux_edata.keys() != self.edge_confidence.keys():
            raise ValueError("Edge set is different to edge confidence keys")
        node_set = set(self.graph.nodes)
        if not node_set.issuperset(self.connectors):
            raise ValueError("Connectors are not attached to a subset of nodes")
        tag_set = set(itertools.chain.from_iterable(self.tags.values()))
        if not node_set.issuperset(tag_set):
            raise ValueError("Tags are not attached to a subset of nodes")

    def _subcopy(self, node_set):
        new_g = self.graph.subgraph(node_set).copy()
        locations = subset_dict(self.node_loc, node_set)
        radius = subset_dict(self.node_radius, node_set)
        edge_conf = subset_dict(
            self.edge_confidence, set(tuple(uv) for uv in new_g.edges), EdgeData()
        )
        connectors = subset_dict(self.connectors, node_set)
        tags = defaultdict(
            list,
            (
                (k, [item for item in v if item in node_set])
                for k, v in self.tags.items()
            ),
        )

        return Arbor(
            self.id,
            new_g,
            locations,
            radius,
            edge_conf,
            connectors,
            tags,
            validate=False,
        )  # type: ignore

    def _get_single_tagged_node(self, tag: str, must_exist=False):
        nodes = self.tags.get(tag, [])
        if len(nodes) == 1:
            return nodes[0]
        elif len(nodes) > 1:
            raise ValueError(f"More than one node tagged with '{tag}'")
        elif must_exist:
            raise ValueError(f"No nodes tagged with '{tag}'")
        else:
            return None

    @property
    def soma(self) -> Optional[TnId]:
        return self._get_single_tagged_node(self.SOMA)

    @property
    def axon_dendrite_split(self) -> Optional[TnId]:
        return self._get_single_tagged_node(self.AXON_SPLIT)

    @property
    def ends(self) -> Set[TnId]:
        return set(self.tags[self.ENDS])

    def axon_nodes(self) -> Iterator[TnId]:
        """
        Returns nodes belonging to the axon (i.e. distal to the split point)
        in sorted DFS order.

        :raises ValueError: Split point not known
        :yield: treenodes belonging to the axon
        """
        split = self.axon_dendrite_split
        if split is None:
            raise ValueError(
                "Unknown axon/dendrite split point: "
                f"should be tagged with {self.AXON_SPLIT}"
            )

        for _, child in dfs_edges(self.graph, split):
            yield child

    @classmethod
    def empty(cls, skid=None):
        return cls(
            skid,
            nx.DiGraph(),
            dict(),
            dict(),
            EdgeData(),
            dict(),
            defaultdict(list),
            validate=False,
        )

    @classmethod
    def from_spacedtree(
        cls, tree: SpacedTree, skid, edge_confidence, connectors, tags, *, validate=True
    ) -> Arbor:
        return cls(
            skid,
            tree.graph,
            tree.node_loc,
            tree.node_radius,
            edge_confidence,
            connectors,
            tags,
            validate=validate,
        )

    def prune_non_branches(self):
        non_branch_nodes = set(self.tags.get(self.NOT_A_BRANCH, []))
        return self.prune_branches_containing(non_branch_nodes)

    def topological_copy(self):
        g, slabs = topological_copy_slabs(self.slabs())
        dists = self.distance_from_root
        edge_length = EdgeData()
        edge_confidence = EdgeData()
        for u, v in g.edges():
            edge_length[u, v] = dists[v] - dists[u]
            edge_confidence[u, v] = min(path_edge_data(slabs[u, v], edge_confidence))

        nodes = set(g.nodes())
        locations = subset_dict(self.node_loc, nodes)
        radius = subset_dict(self.node_loc, nodes)
        connectors = subset_dict(self.connectors, nodes)
        tags = defaultdict(
            list,
            ((k, [item for item in v if item in nodes]) for k, v in self.tags.items()),
        )

        new = Arbor(
            self.id,
            g,
            locations,
            radius,
            edge_confidence,
            connectors,
            tags,
            validate=False,
        )
        new._edge_length = edge_length
        new.is_topological_copy = True
        return new
