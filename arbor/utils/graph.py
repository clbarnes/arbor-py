from typing import Iterator, Set, Optional, Tuple, List, Iterable, Dict

import networkx as nx

from .classes import TnId, EdgeData, CoordXYZ
from .misc import resample_linestring, id_gen


def path_to_root(g: nx.DiGraph, node: TnId) -> Iterator[TnId]:
    """
    Yield given node, then its (unambiguous) ancestors up to and including the root.

    max_edge_lenram node: starting node
    :raises ValueError: A node has more than one parent
    :yield: visited treenodes
    """
    while node is not None:
        yield node
        node = unique_parent(g, node)  # type: ignore


def reroot_graph(g: nx.DiGraph, new_root: int) -> nx.DiGraph:
    """
    Reverse edges as necessary to make new_root the root of the graph.

    :param g: graph
    :param new_root: treenode to become root
    :raises ValueError: Given root is not in the graph, or has ambiguous parentage
    :return: Rerooted graph
    """
    if new_root not in g.nodes:
        raise ValueError("New root is not in the graph")

    g = g.copy()
    to_remove = []
    parent = new_root
    while True:
        child = unique_parent(g, parent)
        if child is None:
            break
        to_remove.append((child, parent))
        parent = child

    for child, parent in to_remove:
        g.remove_edge(child, parent)
        g.add_edge(parent, child)

    return g


def unique_parent(g: nx.DiGraph, node: int) -> Optional[TnId]:
    """
    Find the single parent of a node in a tree graph.

    :param g: graph
    :param node: node
    :raises ValueError: Node has more than one parent
    :return: node, or None if it is the root
    """
    parents = list(g.predecessors(node))
    if len(parents) > 1:
        raise ValueError(f"Node {node} has more than one parent ({parents})")
    if parents:
        return parents[0]
    return None


def topo_sort_edges(g: nx.DiGraph) -> Iterator[Tuple[TnId, TnId]]:
    """
    Return topologically-sorted edges.

    TODO: is this deprecated by dfs_edges?

    :param g: graph
    :yield: parent-child tuples
    """
    child: TnId
    for child in nx.topological_sort(g):
        parent = unique_parent(g, child)
        if parent is not None:
            yield parent, child


def dfs_edges(g: nx.DiGraph, root=None, stop_at=None) -> Iterator[Tuple[TnId, TnId]]:
    """
    Depth first search, where children are addressed in ascending sort order,
    yielding edges.

    :param g: graph
    :param root: root (inferred from graph if not given), defaults to None
    :param stop_at: cut off branches at these nodes
        (these nodes are not visited at all), defaults to None
    :yield: parent-child tuples
    """
    if root is None:
        root = find_root(g)

    if stop_at is None:
        stop_at = set()

    to_visit = [root]

    while to_visit:
        this = to_visit.pop()
        children = sorted(
            (c for c in g.successors(this) if c not in stop_at), reverse=True
        )
        to_visit.extend(children)
        parent = unique_parent(g, this)
        if parent is not None:
            yield parent, this


def find_root(g: nx.DiGraph) -> TnId:
    """
    Find the root of a tree graph

    :param g: tree
    :raises ValueError: 0 or more than 2 roots found
    :return: root node
    """
    roots = [node for node, deg in g.in_degree if deg == 0]
    if len(roots) != 1:
        raise ValueError(f"Found {len(roots)} possible roots")
    return roots[0]


def find_branches_leaves(g: nx.DiGraph) -> Tuple[Dict[TnId, int], Set[TnId]]:
    """
    Find the branch and leaf nodes of a tree.

    :param g: graph
    :return: tuple of branches (dict of treenode to number of children)
        and leaves (set of nodes)
    """
    branches = dict()
    leaves = set()
    for n, d in g.out_degree:
        if d > 1:
            branches[n] = d
        elif d == 0:
            leaves.add(n)
    return branches, leaves


def prune_tree(g: nx.DiGraph, *nodes: TnId) -> Tuple[nx.DiGraph, Set[TnId]]:
    """
    Return a copy of the given graph, with the given nodes and all of their
    predecessors removed.

    :param g: graph
    :return: new graph and set of removed nodes
    """
    g = g.copy()
    removed: Set[TnId] = set()
    for node in nodes:
        if node in removed:
            continue
        to_remove = {node}
        for _, child in dfs_edges(g, node):
            to_remove.add(child)
        g.remove_nodes_from(to_remove)
        removed.update(to_remove)

    return g, removed


def find_slabs(
    g: nx.DiGraph,
    root: Optional[TnId] = None,
    branches: Optional[Iterable[TnId]] = None,
    leaves: Optional[Set[TnId]] = None,
) -> Iterator[List[TnId]]:
    """
    Yield slabs (unbranched leafward run of nodes) from a graph in a depth-first manner.
    The start of each slab will be the root or a branch;
    the end will be a branch or leaf.

    :param g: graph
    :param root: graph root: inferred if not given, defaults to None
    :param branches: graph branches: inferred if not given, defaults to None
    :param leaves: graph leaves: inferred if not given, defaults to None
    :yield: lists of nodes
    """
    if root is None:
        root = find_root(g)
    if branches is None or leaves is None:
        branches, leaves = find_branches_leaves(g)

    terminators = leaves.union(branches)

    slab: List[TnId] = []
    for parent, child in dfs_edges(g, root):
        if not slab:
            slab.append(parent)
        slab.append(child)
        if child in terminators:
            yield slab
            slab = []


def leafward_slab(g: nx.DiGraph, root) -> Tuple[List[TnId], List[TnId]]:
    """
    Find the slab downstream of the given neuron, terminating at a branch or leaf.
    Also returns the children of the termination point.

    :param g: graph
    :param root: starting node
    :return: tuple of slab treenodes and children of slab terminator
    """
    slab = [root]
    while True:
        this_children = sorted(g.successors(slab[-1]))
        if len(this_children) > 1:
            return slab, this_children
        elif len(this_children) == 0:
            return slab, []
        else:
            slab.extend(this_children)


def topological_copy_slabs(
    slabs: Iterable[List[TnId]]
) -> Tuple[nx.DiGraph, EdgeData[List[TnId]]]:
    """
    Construct a graph using only the start and end of each slabs
    (i.e. roots, branches, and leaves).

    :param slabs: slabs of graph
    :return: new graph, and a dict of edge to the slab the edge was constructed from
    """
    full_slabs: EdgeData[List[TnId]] = EdgeData()
    g2 = nx.DiGraph()
    for slab in slabs:
        if len(slab) == 1:
            g2.add_node(slab[0])
        else:
            u = slab[0]
            v = slab[-1]
            g2.add_edge(u, v)
            full_slabs[u, v] = slab
    return g2, full_slabs


def resample_slabs(
    slabs: Iterable[List[TnId]], locations: Dict[TnId, CoordXYZ], max_edge_len: float
) -> Tuple[nx.DiGraph, Dict[TnId, CoordXYZ]]:
    """
    Construct a resampled graph from its slabs.
    The head and tail are unchanged; the remainder of the slab is resampled so that
    its edges are at most max_edge_len long.
    The resampling uses a bicubic kernel.

    :param slabs: slabs of original graph
    :param locations: locations of each treenode in the original
    :param max_edge_len: maximum length of each edge in the resampled graph
    :return: new graph and node locations
    """
    g = nx.DiGraph()
    ids = id_gen(1, set(locations))
    locations = dict()

    for slab in slabs:
        linestring = [locations[n].to_list() for n in slab]
        resampled = resample_linestring(linestring, max_edge_len)

        this_ids = [slab[0]]
        this_ids.extend(TnId(-next(ids)) for _ in range(len(resampled) - 2))
        this_ids.append(slab[-1])

        nx.add_path(g, this_ids)
        for n, loc in zip(this_ids, resampled):
            locations[n] = CoordXYZ(loc)

    return g, locations
