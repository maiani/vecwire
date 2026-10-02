"""Capacitor and inductor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..geometry import positive, positive_int

if TYPE_CHECKING:
    from ..core import Circuit, NodeRef


def capacitor(
    circuit: Circuit,
    start: NodeRef,
    end: NodeRef,
    *,
    id: str | None = None,
    plate_width: float = 14,
    gap: float = 4,
    color: str | None = None,
) -> None:
    """Draw a two-terminal capacitor with leads and parallel plates."""
    branch = circuit.branch(start, end)
    plate_width, gap = positive(plate_width, "plate_width"), positive(gap, "gap")
    if gap >= branch.length:
        raise ValueError("Capacitor gap must be shorter than terminal separation")
    group = circuit.group("capacitor", id, branch=branch)
    first, second = (branch.length - gap) / 2, (branch.length + gap) / 2
    circuit.line(group, branch.start.position, branch.at(first), color=color)
    circuit.line(group, branch.at(second), branch.end.position, color=color)
    for along in (first, second):
        circuit.line(
            group,
            branch.at(along, -plate_width / 2),
            branch.at(along, plate_width / 2),
            color=color,
            width=1.3,
        )


def inductor(
    circuit: Circuit,
    start: NodeRef,
    end: NodeRef,
    *,
    id: str | None = None,
    turns: int = 4,
    color: str | None = None,
) -> None:
    """Draw an inductor as consecutive half-turns between its terminals."""
    branch = circuit.branch(start, end)
    turns = positive_int(turns, "turns")
    group = circuit.group("inductor", id, branch=branch)
    radius = branch.length / (2 * turns)
    # Bulge to the same side of the screen whatever the terminal order.
    dx, dy = branch.direction
    sweep = 1 if dy > 0 or dx < 0 else 0
    commands = [("M", *branch.start.position)]
    for index in range(1, turns + 1):
        commands.append(("A", radius, radius, 0, 0, sweep, *branch.at(2 * radius * index)))
    circuit.path(group, commands, color=color)
