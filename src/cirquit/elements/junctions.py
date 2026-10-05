"""Josephson junctions: the bare X, boxed harmonic junctions, and their sums.

``junction`` draws the standard symbol, a bare X, which says nothing about the
current-phase relation. ``harmonic_junction`` draws the boxed symbol of one
tunnelling harmonic: a square crossed by ``m`` diagonals each way stands for a
``cos(m phi)`` term, in which ``m`` Cooper pairs tunnel together, and two dots
mark the odd ``sin(m phi)`` term of a phi0 junction. For ``m = 1`` the boxed
symbol is the bare X inside its square. ``harmonic_sum`` composes boxed glyphs
into a multiharmonic junction.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING

from ..geometry import Box, Branch, Point, positive, positive_int

if TYPE_CHECKING:
    from lxml import etree

    from ..core import Circuit, NodeRef

JUNCTION_KINDS = ("cos", "sin")


def _kind(value: str) -> str:
    if value not in JUNCTION_KINDS:
        raise ValueError("kind must be 'cos' or 'sin'")
    return value


def _glyph_branch(
    circuit: Circuit, start: NodeRef, end: NodeRef, size: float
) -> tuple[Branch, float]:
    """Return the branch and the checked glyph size, which must fit between the terminals."""
    branch = circuit.branch(start, end)
    size = positive(size, "size")
    if size >= branch.length:
        raise ValueError("Junction glyph must be shorter than terminal separation")
    return branch, size


def _leads(
    circuit: Circuit, group: etree._Element, branch: Branch, size: float, color: str | None
) -> None:
    """Draw the two leads from the terminals to the edge of a centred box of side ``size``."""
    centre = branch.length / 2
    circuit.line(group, branch.start.position, branch.at(centre - size / 2), color=color)
    circuit.line(group, branch.at(centre + size / 2), branch.end.position, color=color)


def junction(
    circuit: Circuit,
    start: NodeRef,
    end: NodeRef,
    *,
    id: str | None = None,
    size: float = 7.2,
    color: str | None = None,
    lead_color: str | None = None,
) -> None:
    """Draw a Josephson junction as the bare X, with two leads.

    The X spans the diagonals of a ``size`` square centred on the branch. The
    leads run on to the centre of the X, so the wire is continuous through it.
    ``color`` sets the X and, unless ``lead_color`` is given, the leads.
    """
    branch, size = _glyph_branch(circuit, start, end, size)
    group = circuit.group("josephson-junction", id, branch=branch)
    centre = branch.length / 2
    middle = branch.at(centre)
    leads = lead_color or color
    circuit.line(group, branch.start.position, middle, color=leads)
    circuit.line(group, middle, branch.end.position, color=leads)
    for sign in (-1, 1):
        circuit.line(
            group,
            branch.at(centre - size / 2, sign * size / 2),
            branch.at(centre + size / 2, -sign * size / 2),
            color=color,
        )


def harmonic_junction(
    circuit: Circuit,
    start: NodeRef,
    end: NodeRef,
    order: int = 1,
    *,
    kind: str = "cos",
    id: str | None = None,
    size: float = 7.2,
    color: str | None = None,
    lead_color: str | None = None,
) -> None:
    """Draw the boxed junction symbol of one tunnelling harmonic, with two leads.

    The square is crossed by ``order`` diagonals in each direction, for a
    ``cos(order * phi)`` term that transfers ``order`` Cooper pairs.
    ``kind="sin"`` adds two dots for the odd ``sin(order * phi)`` term of a
    phi0 junction. ``color`` sets the glyph and, unless ``lead_color`` is
    given, the leads. The group records ``data-harmonic`` and ``data-kind``.
    """
    branch, size = _glyph_branch(circuit, start, end, size)
    kind = _kind(kind)
    order = positive_int(order, "order")
    group = circuit.group(
        "josephson-junction", id, branch=branch, data={"harmonic": order, "kind": kind}
    )
    _leads(circuit, group, branch, size, lead_color or color)
    harmonic_glyph(circuit, group, branch.at(branch.length / 2), size, order, kind, color)


def harmonic_glyph(
    circuit: Circuit,
    parent: etree._Element,
    center: Point,
    size: float,
    order: int,
    kind: str = "cos",
    color: str | None = None,
) -> None:
    """Draw the boxed harmonic glyph, without leads, into ``parent``.

    A square of side ``size`` holds ``order`` parallel diagonals each way,
    clipped to the square; ``kind="sin"`` adds the two dots. The glyph is
    symmetric under quarter turns, so it needs no orientation.
    """
    half = size / 2
    cx, cy = center
    circuit.rect(parent, (cx - half, cy - half), (cx + half, cy + half), color=color)
    # Diagonals b = s*a + c in local coordinates, clipped to the square.
    pitch = 0.9 * size / order
    hatch = circuit.stroke_width * (1 if order == 1 else 0.75)
    for slope in (1, -1):
        for index in range(order):
            c = (index - (order - 1) / 2) * pitch
            lo, hi = max(-half, -half - slope * c), min(half, half - slope * c)
            circuit.line(
                parent,
                (cx + lo, cy + slope * lo + c),
                (cx + hi, cy + slope * hi + c),
                color=color,
                width=hatch,
            )
    if kind == "sin":
        for sign in (-1, 1):
            circuit.dot(parent, (cx + sign * 0.27 * size, cy), 0.075 * size + 0.1, color)


def harmonic_sum(
    circuit: Circuit,
    start: NodeRef,
    end: NodeRef,
    orders: Sequence[int] = (1, 2, 3),
    *,
    id: str | None = None,
    kinds: str | Sequence[str] = "cos",
    colors: str | Sequence[str | None] | None = None,
    ellipsis: bool = True,
    size: float = 7.2,
    spacing: float | None = None,
    padding: float = 2.4,
    lead_color: str | None = None,
    box_color: str | None = None,
    dash: Sequence[float] = (2.2, 1.6),
    corner_radius: float = 2,
    rails: bool = True,
) -> Box:
    """Draw a multiharmonic junction as a dashed box holding a sum of harmonics.

    The box is centred on the branch between the terminals; the sum
    ``m=1 + m=2 + ...`` reads left to right on a vertical branch and top to
    bottom on a horizontal one. Each term is a boxed ``harmonic_glyph``. The
    harmonics of one junction add as energies, so the terms are elements in
    parallel: by default each term hangs between two rails inside the box, and
    the branch leads join the rails. ``rails=False`` instead ends each term's
    leads in terminal dots, a shorthand sum notation. Returns the box bounds;
    ``Box.terms`` holds the glyph centres for per-term labels.
    """
    branch = circuit.branch(start, end)
    if not orders:
        raise ValueError("orders must contain at least one harmonic")
    orders = [positive_int(order, "order") for order in orders]
    count = len(orders)
    kinds = [kinds] * count if isinstance(kinds, str) else list(kinds)
    palette = [colors] * count if colors is None or isinstance(colors, str) else list(colors)
    if len(kinds) != count or len(palette) != count:
        raise ValueError("kinds and colors must match the number of orders")
    kinds = [_kind(kind) for kind in kinds]
    size = positive(size, "size")
    spacing = 2.2 * size if spacing is None else positive(spacing, "spacing")
    padding = positive(padding, "padding")
    stub = 0.45 * size
    half_along = size / 2 + stub + padding
    if 2 * half_along >= branch.length:
        raise ValueError("harmonic_sum box must be shorter than terminal separation")
    # Across offsets: glyph centres, then an optional "+ ..." tail.
    normal = branch.normal
    reading = (abs(normal[0]), abs(normal[1]))
    centres = [index * spacing for index in range(count)]
    extent = [-size / 2, centres[-1] + size / 2]
    if ellipsis:
        dots_at = centres[-1] + spacing * 0.95
        extent[1] = dots_at + 0.3 * size + 0.6
    shift = -(extent[0] + extent[1]) / 2
    mid = branch.length / 2

    def place(along: float, across: float) -> Point:
        """Point at ``along`` from the box centre and ``across`` in reading order."""
        x, y = branch.at(mid + along)
        return x + reading[0] * (across + shift), y + reading[1] * (across + shift)

    group = circuit.group(
        "harmonic-sum", id, branch=branch, data={"orders": " ".join(map(str, orders))}
    )
    reach = size / 2 + stub  # glyph centre to a rail or terminal dot
    outer = reach if rails else half_along
    circuit.line(group, branch.start.position, place(-outer, -shift), color=lead_color)
    circuit.line(group, place(outer, -shift), branch.end.position, color=lead_color)
    bounds = circuit.rect(
        group,
        place(-half_along, extent[0] - padding),
        place(half_along, extent[1] + padding),
        color=box_color,
        width=0.75 * circuit.stroke_width,
        corner_radius=corner_radius,
        dash=dash,
    )
    if rails:
        # The rails run on to the ellipsis: further terms hang there too.
        span = (min(centres[0], -shift), max(dots_at if ellipsis else centres[-1], -shift))
        for sign, side in ((-1, "top"), (1, "bottom")):
            rail = circuit.group("rail", None if id is None else f"{id}-rail-{side}", parent=group)
            circuit.line(
                rail, place(sign * reach, span[0]), place(sign * reach, span[1]), color=lead_color
            )
    dot_radius = 0.9 * circuit.stroke_width
    terms = []
    for order, kind, color, across in zip(orders, kinds, palette, centres, strict=True):
        term = circuit.group(
            "josephson-junction",
            None if id is None else f"{id}-m{order}",
            parent=group,
            data={"harmonic": order, "kind": kind},
        )
        for sign in (-1, 1):
            tip = place(sign * reach, across)
            circuit.line(term, place(sign * size / 2, across), tip, color=lead_color)
            if not rails:
                circuit.dot(term, tip, dot_radius, lead_color)
        harmonic_glyph(circuit, term, place(0, across), size, order, kind, color)
        terms.append(place(0, across))
    signs = [(left + right) / 2 for left, right in pairwise(centres)]
    if ellipsis:
        signs.append(centres[-1] + spacing * 0.45)
    arm = 0.28 * size
    for across in signs:
        cx, cy = place(0, across)
        plus = circuit.group("plus", parent=group)
        circuit.line(plus, (cx - arm, cy), (cx + arm, cy), color=lead_color)
        circuit.line(plus, (cx, cy - arm), (cx, cy + arm), color=lead_color)
    if ellipsis:
        more = circuit.group("ellipsis", parent=group)
        for step in (-1, 0, 1):
            circuit.dot(more, place(0, dots_at + step * 0.3 * size), 0.6, lead_color)
    return replace(bounds, terms=tuple(terms))
