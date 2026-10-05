"""Points, bounds, and branches shared by the canvas and the symbol library.

This module imports nothing else from cirquit except ``Node``, so both the core
canvas and the symbols in ``cirquit.elements`` can use it.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite

from .node import Node

Point = tuple[float, float]


def point(value: Point) -> Point:
    """Return ``value`` as a pair of finite floats, or raise ``ValueError``."""
    if len(value) != 2 or not all(isfinite(v) for v in value):
        raise ValueError("A point must contain two finite coordinates")
    return float(value[0]), float(value[1])


def positive(value: float, name: str) -> float:
    """Return ``value`` as a float if it is finite and positive."""
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return float(value)


def nonnegative(value: float, name: str) -> float:
    """Return ``value`` as a float if it is finite and not negative."""
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


def positive_int(value: int, name: str) -> int:
    """Return ``value`` if it is a positive integer (``bool`` is rejected)."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def offset(
    origin: Point, direction: Point, normal: Point, along: float, across: float = 0.0
) -> Point:
    """Move ``along`` units in ``direction`` and ``across`` units along ``normal``."""
    return (
        origin[0] + direction[0] * along + normal[0] * across,
        origin[1] + direction[1] * along + normal[1] * across,
    )


@dataclass(frozen=True, slots=True)
class Box:
    """Axis-aligned bounds of a drawn element, for placing labels next to it.

    ``terms`` lists the glyph centres of a ``harmonic_sum`` in reading order.
    """

    left: float
    top: float
    right: float
    bottom: float
    terms: tuple[Point, ...] = ()

    @property
    def center(self) -> Point:
        return (self.left + self.right) / 2, (self.top + self.bottom) / 2

    def at(self, anchor: str = "cc") -> Point:
        """Return a point on the box using the ``l/c/r`` + ``t/c/b`` label anchors."""
        if len(anchor) != 2 or anchor[0] not in "lcr" or anchor[1] not in "tcb":
            raise ValueError("anchor must combine l/c/r with t/c/b")
        x = {"l": self.left, "c": (self.left + self.right) / 2, "r": self.right}[anchor[0]]
        y = {"t": self.top, "c": (self.top + self.bottom) / 2, "b": self.bottom}[anchor[1]]
        return x, y


@dataclass(frozen=True, slots=True)
class Branch:
    """The straight, horizontal or vertical run between two terminal nodes.

    Two-terminal symbols are drawn in branch coordinates: ``along`` is the
    distance from ``start`` towards ``end`` and ``across`` the distance along
    ``normal``, the direction a quarter turn clockwise on screen. ``at(along,
    across)`` converts to drawing coordinates, so one symbol definition serves
    every orientation.
    """

    start: Node
    end: Node

    def __post_init__(self) -> None:
        dx, dy = self.end.x - self.start.x, self.end.y - self.start.y
        if dx == 0 and dy == 0:
            raise ValueError("Component terminals must be distinct")
        if dx != 0 and dy != 0:
            raise ValueError("Components must be horizontal or vertical")

    @property
    def length(self) -> float:
        return hypot(self.end.x - self.start.x, self.end.y - self.start.y)

    @property
    def direction(self) -> Point:
        """Unit vector from ``start`` to ``end``."""
        length = self.length
        return (self.end.x - self.start.x) / length, (self.end.y - self.start.y) / length

    @property
    def normal(self) -> Point:
        """Unit vector perpendicular to ``direction``."""
        dx, dy = self.direction
        return -dy, dx

    def at(self, along: float, across: float = 0.0) -> Point:
        """Return the drawing coordinates of a point given in branch coordinates."""
        return offset(self.start.position, self.direction, self.normal, along, across)
