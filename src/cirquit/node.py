"""Placed connection points in a circuit schematic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Node:
    """A named connection point at one position in the drawing.

    Wires may join several placed nodes into one electrical net. A node is a
    connection point, not a claim that its name identifies an entire net.
    """

    name: str
    x: float
    y: float

    @property
    def position(self) -> tuple[float, float]:
        return self.x, self.y
