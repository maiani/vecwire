"""Ground symbol."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..geometry import offset

if TYPE_CHECKING:
    from ..core import Circuit, NodeRef

# Direction of the stem, and the direction the bars extend across it.
_FRAMES = {
    "down": ((0, 1), (1, 0)),
    "up": ((0, -1), (1, 0)),
    "left": ((-1, 0), (0, 1)),
    "right": ((1, 0), (0, 1)),
}


def ground(
    circuit: Circuit,
    node: NodeRef,
    *,
    id: str | None = None,
    direction: str = "down",
    color: str | None = None,
) -> None:
    """Draw a ground symbol connected to ``node``: a short stem and three bars."""
    connected = circuit.resolve(node)
    if direction not in _FRAMES:
        raise ValueError("direction must be down, up, left, or right")
    axis, across = _FRAMES[direction]
    origin = connected.position
    group = circuit.group("ground", id, data={"node": connected.name})
    circuit.line(group, origin, offset(origin, axis, across, 4), color=color)
    for distance, half_width in ((4, 6), (6.4, 3.8), (8.8, 1.6)):
        circuit.line(
            group,
            offset(origin, axis, across, distance, -half_width),
            offset(origin, axis, across, distance, half_width),
            color=color,
        )
