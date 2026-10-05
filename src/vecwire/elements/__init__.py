"""The circuit-symbol library.

Every symbol is a plain function whose first argument is the ``Circuit`` it
draws on, e.g. ``capacitor(circuit, "top", "bottom", id="C")``. Symbols draw
only through the circuit's public drawing API (``branch``, ``group``, ``line``,
``rect``, ``dot``, ``path``) and the helpers in ``vecwire.geometry``, so adding
one never requires a change to the core canvas. The built-in symbols are also
bound as ``Circuit`` methods: ``circuit.capacitor("top", "bottom")``.
"""

from .ground import ground
from .junctions import JUNCTION_KINDS, harmonic_glyph, harmonic_junction, harmonic_sum, junction
from .passive import capacitor, inductor

__all__ = [
    "JUNCTION_KINDS",
    "capacitor",
    "ground",
    "harmonic_glyph",
    "harmonic_junction",
    "harmonic_sum",
    "inductor",
    "junction",
]
