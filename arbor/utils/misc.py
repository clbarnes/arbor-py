from __future__ import annotations
from typing import Iterator, Iterable, MutableMapping, Optional, Mapping, TypeVar, Set

import numpy as np
from scipy.interpolate import interp1d

from .classes import EdgeData, ValueType

SPLIT_TAG = "mw axon split"
SOMA_TAG = "soma"
NOT_A_BRANCH = "not a branch"


def resample_linestring(linestring: np.ndarray, max_edge_len: float) -> np.ndarray:
    """
    Resample a linestring (as an Nx3 array).
    Its head and tail do not move.
    Sampling uses cubic interpolation.
    New edges are at most max_edge_len long (probably shorter).

    :param linestring: Nx3 ndarray
    :param max_edge_len: maximum length of new edges
    :return: Nx3 ndarray
    """
    linestring = np.asarray(linestring, copy=True)
    edge_lengths = np.linalg.norm(np.diff(linestring, axis=0), axis=1)
    cumu_lengths = np.insert(np.cumsum(edge_lengths), 0, 0)
    length = cumu_lengths[-1]

    # ceil to over-sample (so that max_edge_len is max)
    # +1 to give us fenceposts, rather than fences
    n_samples = int(np.ceil(length / max_edge_len)) + 1
    if n_samples < 3:
        return linestring

    f = interp1d(cumu_lengths, linestring, kind="cubic", axis=0)
    linestring[1:-1] = f(np.linspace(0, length, n_samples)[1:-1])
    return linestring


def path_edge_data(
    path: Iterable[int], edge_data: EdgeData[ValueType]
) -> Iterator[ValueType]:
    """
    Yield values from a dict whose keys are edge indices;
    infer the edges from the given path.

    :param path: path of nodes
    :param edge_data: data to return from
    :yield: values associated with each edge in the path
    """
    it = iter(path)
    parent = next(it)
    for child in it:
        yield edge_data[parent, child]
        parent = child


def id_gen(start=0, skip=None) -> Iterator[int]:
    if skip is None:
        skip = set()
    while True:
        while start in skip:
            start += 1
        yield start
        start += 1


K = TypeVar("K")
V = TypeVar("V")


def subset_dict(
    data: Mapping[K, V], keys: Set, out: Optional[MutableMapping[K, V]] = None
) -> MutableMapping[K, V]:
    if out is None:
        out = dict()

    for k in keys.intersection(data):
        out[k] = data[k]

    return out
