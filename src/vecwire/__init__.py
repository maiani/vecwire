"""Editable SVG schematics for electrical and circuit-QED circuits.

``Circuit`` (in ``vecwire.core``) is the canvas; the symbols live in
``vecwire.elements`` and are also available as ``Circuit`` methods.
"""

from . import elements
from .core import Circuit
from .geometry import Box, Branch
from .node import Node

__version__ = "0.3.0"

__all__ = ["Box", "Branch", "Circuit", "Node", "__version__", "elements"]
