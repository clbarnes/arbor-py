# -*- coding: utf-8 -*-

"""Top-level package for arbor."""

from .version import __version__
from .arbor import Arbor
from .spaced_tree import SpacedTree
from .utils.classes import CoordXYZ, TnId, SkId, EdgeData

__author__ = """Chris L. Barnes"""
__email__ = "chrislloydbarnes@gmail.com"
__version_info__ = tuple(int(n) for n in __version__.split("."))

__all__ = ["Arbor", "SpacedTree", "CoordXYZ", "TnId", "SkId", "EdgeData"]
