from typing import List, Any, Dict, DefaultDict
import itertools
from collections import defaultdict

import networkx as nx

from .arbor import Arbor
from .utils.graph import topo_sort_edges
from .utils.classes import (
    EdgeData,
    CoordXYZ,
    TreenodeConnector,
    ConnectorRelation,
    TnId,
)


def arbor_to_dict(arbor: Arbor):
    columns = ["treenode", "parent", "x", "y", "z", "radius", "confidence"]
    node = arbor.root
    row: List[Any] = [node, None]
    row += arbor.node_loc[node].to_list()
    row.append(arbor.node_radius[node])
    row.append(None)
    table = [row]

    for parent, node in topo_sort_edges(arbor.graph):
        row = [node, parent]
        row += arbor.node_loc[node].to_list()
        row.append(arbor.node_radius[node])
        row.append(arbor.edge_confidence[parent, node])
        table.append(row)

    conn_columns = ["treenode", "connector", "relation", "x", "y", "z"]
    conn_data = []
    for tn, conn, relation, loc in sorted(
        itertools.chain.from_iterable(arbor.connectors.values())
    ):
        conn_data.append([tn, conn, relation.value] + loc.to_list())

    return {
        "id": arbor.id,
        "graph": {"columns": columns, "data": table},
        "connectors": {"columns": conn_columns, "data": conn_data},
        "tags": arbor.tags,
    }


def dict_to_arbor(d: Dict[str, Any]):
    graph = nx.DiGraph()
    node_loc = dict()
    node_radius = dict()
    edge_confidence: EdgeData[int] = EdgeData()

    graph_rows = d["graph"]["data"].copy()
    root_row = graph_rows.pop(0)
    node = root_row[0]
    node_loc[node] = CoordXYZ(root_row[2:5])
    node_radius[node] = root_row[5]

    for node, parent, x, y, z, radius, confidence in graph_rows:
        graph.add_edge(parent, node)
        node_loc[node] = CoordXYZ([x, y, z])
        node_radius[node] = radius
        edge_confidence[parent, node] = confidence

    connectors: DefaultDict[TnId, List[TreenodeConnector]] = defaultdict(list)

    for node, conn, relation_value, x, y, z in d["connectors"]["data"]:
        tn_conn = TreenodeConnector(
            node, conn, ConnectorRelation(relation_value), CoordXYZ([x, y, z])
        )
        connectors[TnId(node)].append(tn_conn)

    tags = defaultdict(list, d["tags"])

    return Arbor(
        d["skid"], graph, node_loc, node_radius, edge_confidence, dict(connectors), tags
    )
