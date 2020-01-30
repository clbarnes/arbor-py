from typing import (
    Tuple,
    TypeVar,
    NewType,
    Generic,
    NamedTuple,
    Dict,
    Sequence,
    Iterator,
)
from collections.abc import MutableMapping
from copy import copy
from enum import IntEnum

from coordinates import Coordinate


EdgeKeyType = Tuple[int, int]
ValueType = TypeVar("ValueType")

TnId = NewType("TnId", int)
SkId = NewType("SkId", int)


class CoordXYZ(Coordinate):
    default_order = tuple("xyz")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self):
        """Raise a ValueError if the instance's keys are incorrect"""
        if set(self.default_order) != set(self):
            raise ValueError(
                "{} needs keys {} and got {}".format(
                    type(self).__name__, self.default_order, tuple(self)
                )
            )


class ConnectorRelation(IntEnum):
    """
    The relationship of a skeleton's treenode to a connector node.

    e.g.
    - a "sending" treenode is PRESYNAPTIC_TO a connector
    - a "receiving" treenode is POSTSYNAPTIC_TO a connector
    """

    OTHER = -1
    PRESYNAPTIC_TO = 0
    POSTSYNAPTIC_TO = 1
    GAP_JUNCTION = 2


class EdgeData(MutableMapping, Generic[ValueType]):
    def __init__(self, *args, **kwargs):
        self._dict: Dict[EdgeKeyType, ValueType] = dict()
        self.update(dict(*args, **kwargs))

    @staticmethod
    def _key(arg):
        if arg[0] > arg[1]:
            arg = arg[1], arg[0]
        return arg

    def __setitem__(self, k: Sequence[int], v: ValueType) -> None:
        self._dict[self._key(k)] = v

    def __delitem__(self, v: Sequence[int]) -> None:
        del self._dict[self._key(v)]

    def __getitem__(self, k: Sequence[int]) -> ValueType:
        return self._dict[self._key(k)]

    def __len__(self) -> int:
        return len(self._dict)

    def __iter__(self) -> Iterator[EdgeKeyType]:
        yield from self._dict

    def edges(self):
        return {frozenset(pair) for pair in self}


class TreenodeConnector(NamedTuple):
    treenode: TnId
    connector: int
    relation: ConnectorRelation
    loc: CoordXYZ

    def __copy__(self):
        return self.copy()

    def copy(self, treenode=None, connector=None, relation=None, loc=None):
        d = self._asdict()
        d["loc"] = copy(d["loc"]) if loc is None else loc
        if treenode is not None:
            d["treenode"] = treenode

        if connector is not None:
            d["connector"] = connector

        if relation is not None:
            d["relation"] = relation

        return TreenodeConnector(**d)
