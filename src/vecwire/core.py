"""The schematic canvas: nodes, wires, labels, enclosures, and the SVG document.

``Circuit`` owns everything that is not a circuit symbol: the SVG root and its
ids, placed nodes, wire routing, labels, dashed boxes, and serialization. It
also offers the small drawing API the symbols in ``vecwire.elements`` are built
from (``branch``, ``group``, ``line``, ``rect``, ``dot``, ``path``), so a new
symbol is written against that API alone and never needs a change here.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from copy import deepcopy
from itertools import pairwise
from math import acos, hypot, tan
from pathlib import Path
from typing import Protocol, runtime_checkable

from lxml import etree

from . import elements
from .geometry import Box, Branch, Point, nonnegative, point, positive
from .node import Node

SVG_NS = "http://www.w3.org/2000/svg"

type NodeRef = Node | str
# A path command letter followed by its numbers, e.g. ``("M", x, y)``.
type PathCommand = tuple[str, *tuple[float, ...]]


@runtime_checkable
class Fragment(Protocol):
    """An SVG fragment accepted as a label, such as a VecTeX fragment.

    It has a size in user units and serializes to one SVG element, usually a
    ``<g>``, with its origin at the top-left corner. Matching is structural:
    any object with these three members qualifies, so VecTeX stays optional.
    """

    @property
    def width(self) -> float: ...

    @property
    def height(self) -> float: ...

    def to_svg(self) -> str: ...


def _number(value: float) -> str:
    # Twelve significant digits hide floating-point noise, keeping output stable.
    return format(float(value), ".12g")


def _tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


class Circuit:
    """A schematic drawn in SVG user units (usually points).

    Nodes are named, positioned connection points. Components include their own
    leads, while ``wire`` joins nodes and optional route points shape the path.
    Horizontal and vertical placement are supported for two-terminal symbols.
    """

    def __init__(
        self,
        width: float,
        height: float,
        *,
        unit: str = "pt",
        stroke: str = "#262626",
        stroke_width: float = 0.9,
        linecap: str = "round",
        linejoin: str = "round",
        corner_radius: float = 0,
    ) -> None:
        self.width = positive(width, "width")
        self.height = positive(height, "height")
        if unit not in {"pt", "px", "mm"}:
            raise ValueError("unit must be 'pt', 'px', or 'mm'")
        self.unit = unit
        self.stroke = stroke
        self.stroke_width = positive(stroke_width, "stroke_width")
        self.linecap = self._linecap(linecap)
        self.linejoin = self._linejoin(linejoin)
        self.corner_radius = nonnegative(corner_radius, "corner_radius")
        self._root = etree.Element(
            _tag("svg"),
            # lxml-stubs types nsmap as Mapping[str, str], but lxml takes the
            # None key for the default namespace; without it every tag is prefixed.
            nsmap={None: SVG_NS},  # ty: ignore[invalid-argument-type]
            width=f"{_number(self.width)}{unit}",
            height=f"{_number(self.height)}{unit}",
            viewBox=f"0 0 {_number(self.width)} {_number(self.height)}",
        )
        self._ids: set[str] = set()
        self._nodes: dict[str, Node] = {}
        self._visible_nodes: list[etree._Element] = []

    # Built-in symbols. Each is a plain function in ``vecwire.elements`` whose
    # first argument is the circuit, so binding it here makes
    # ``circuit.capacitor(a, b)`` the same call as ``capacitor(circuit, a, b)``.
    capacitor = elements.capacitor
    inductor = elements.inductor
    junction = elements.junction
    harmonic_junction = elements.harmonic_junction
    harmonic_sum = elements.harmonic_sum
    ground = elements.ground

    @staticmethod
    def _linecap(value: str) -> str:
        if value not in {"butt", "round", "square"}:
            raise ValueError("linecap must be butt, round, or square")
        return value

    @staticmethod
    def _linejoin(value: str) -> str:
        if value not in {"miter", "round", "bevel"}:
            raise ValueError("linejoin must be miter, round, or bevel")
        return value

    # ------------------------------------------------------------ nodes

    def node(
        self,
        name: str,
        at: Point,
        *,
        dot: bool = False,
        radius: float = 1.6,
        color: str | None = None,
    ) -> Node:
        """Create a positioned connection point and optionally show its dot."""
        x, y = point(at)
        radius = positive(radius, "radius")
        group = self.group("node", name, data={"x": _number(x), "y": _number(y)})
        node = Node(name, x, y)
        self._nodes[name] = node
        if dot:
            self.dot(group, (x, y), radius, color)
            self._visible_nodes.append(group)
        return node

    def nodes(self, *, dots: Collection[str] = (), **positions: Point) -> dict[str, Node]:
        """Declare several named nodes together; ``dots`` selects visible junctions."""
        unknown = set(dots) - positions.keys()
        if unknown:
            raise ValueError(f"Dots refer to undeclared nodes: {sorted(unknown)!r}")
        return {name: self.node(name, at, dot=name in dots) for name, at in positions.items()}

    def row(self, y: float, *, dots: Collection[str] = (), **x_positions: float) -> dict[str, Node]:
        """Declare nodes sharing a y coordinate; this draws no wire."""
        return self.nodes(dots=dots, **{name: (x, y) for name, x in x_positions.items()})

    def column(
        self, x: float, *, dots: Collection[str] = (), **y_positions: float
    ) -> dict[str, Node]:
        """Declare nodes sharing an x coordinate; this draws no wire."""
        return self.nodes(dots=dots, **{name: (x, y) for name, y in y_positions.items()})

    def resolve(self, node: NodeRef) -> Node:
        """Return the ``Node`` named by ``node``, which must belong to this circuit."""
        if isinstance(node, str):
            if node not in self._nodes:
                raise ValueError(f"Unknown node: {node!r}")
            return self._nodes[node]
        if not isinstance(node, Node) or self._nodes.get(node.name) is not node:
            raise ValueError("Expected a Node created by this Circuit")
        return node

    def branch(self, start: NodeRef, end: NodeRef) -> Branch:
        """Return the straight run between two terminals of a two-terminal symbol."""
        return Branch(self.resolve(start), self.resolve(end))

    def _position(self, at: NodeRef | Point) -> Point:
        return self.resolve(at).position if isinstance(at, (Node, str)) else point(at)

    # ------------------------------------------------------------ drawing API

    def group(
        self,
        kind: str,
        id: str | None = None,
        *,
        parent: etree._Element | None = None,
        branch: Branch | None = None,
        data: Mapping[str, object] | None = None,
    ) -> etree._Element:
        """Open a semantic SVG group ``<g data-component=kind>`` for one drawn item.

        ``id`` must be unique in the document; node names share the same ids.
        ``branch`` records the terminals as ``data-from`` and ``data-to``, and
        ``data`` adds further ``data-*`` attributes in the order given. Groups
        are appended to the document root unless ``parent`` is given.
        """
        if id is not None:
            if not id or id in self._ids:
                raise ValueError(f"Duplicate or empty SVG id: {id!r}")
            self._ids.add(id)
        attrs = {"data-component": kind}
        if id is not None:
            attrs["id"] = id
        group = etree.SubElement(self._root if parent is None else parent, _tag("g"), attrs)
        if branch is not None:
            group.set("data-from", branch.start.name)
            group.set("data-to", branch.end.name)
        for key, value in (data or {}).items():
            group.set(f"data-{key}", str(value))
        return group

    def line(
        self,
        parent: etree._Element,
        start: Point,
        end: Point,
        *,
        color: str | None = None,
        width: float | None = None,
    ) -> None:
        """Draw a straight stroke; colour and width default to the circuit ink."""
        etree.SubElement(
            parent,
            _tag("line"),
            {
                "x1": _number(start[0]),
                "y1": _number(start[1]),
                "x2": _number(end[0]),
                "y2": _number(end[1]),
                "stroke": color or self.stroke,
                "stroke-width": _number(width or self.stroke_width),
                "stroke-linecap": self.linecap,
            },
        )

    def path(
        self,
        parent: etree._Element,
        commands: Iterable[PathCommand],
        *,
        color: str | None = None,
        width: float | None = None,
        linecap: str | None = None,
        linejoin: str | None = None,
    ) -> None:
        """Draw an unfilled path from commands such as ``("M", x, y)`` or ``("A", ...)``.

        Numbers are formatted here, so every symbol serializes coordinates the
        same way and the output stays byte-stable.
        """
        d = " ".join(
            " ".join([name, *(_number(value) for value in values)]) for name, *values in commands
        )
        etree.SubElement(
            parent,
            _tag("path"),
            {
                "d": d,
                "fill": "none",
                "stroke": color or self.stroke,
                "stroke-width": _number(width or self.stroke_width),
                "stroke-linecap": self.linecap if linecap is None else self._linecap(linecap),
                "stroke-linejoin": self.linejoin if linejoin is None else self._linejoin(linejoin),
            },
        )

    def rect(
        self,
        parent: etree._Element,
        first: Point,
        second: Point,
        *,
        color: str | None = None,
        width: float | None = None,
        corner_radius: float = 0,
        dash: Sequence[float] = (),
    ) -> Box:
        """Draw an unfilled rectangle between two opposite corners; return its bounds."""
        left, right = sorted((first[0], second[0]))
        top, bottom = sorted((first[1], second[1]))
        attrs = {
            "x": _number(left),
            "y": _number(top),
            "width": _number(right - left),
            "height": _number(bottom - top),
            "fill": "none",
            "stroke": color or self.stroke,
            "stroke-width": _number(width or self.stroke_width),
            "stroke-linejoin": self.linejoin,
        }
        if corner_radius:
            attrs["rx"] = attrs["ry"] = _number(corner_radius)
        if dash:
            attrs["stroke-dasharray"] = " ".join(
                _number(positive(value, "dash length")) for value in dash
            )
        etree.SubElement(parent, _tag("rect"), attrs)
        return Box(left, top, right, bottom)

    def dot(
        self, parent: etree._Element, at: Point, radius: float, color: str | None = None
    ) -> None:
        """Draw a filled circle, e.g. a connection dot."""
        etree.SubElement(
            parent,
            _tag("circle"),
            {
                "cx": _number(at[0]),
                "cy": _number(at[1]),
                "r": _number(radius),
                "fill": color or self.stroke,
            },
        )

    # ------------------------------------------------------------ wires

    def wire(
        self,
        start: NodeRef,
        end: NodeRef,
        *through: NodeRef,
        via: tuple[Point, ...] = (),
        id: str | None = None,
        color: str | None = None,
        linecap: str | None = None,
        linejoin: str | None = None,
        corner_radius: float | None = None,
    ) -> None:
        """Connect nodes in path order; ``via`` routes between two endpoints without adding nodes.

        All positional nodes are visited in the order given, so
        ``wire("left", "middle", "right")`` draws left to middle to right. A
        route that doubles back on itself is rejected, since it usually means
        the nodes were listed out of order.
        """
        if through and via:
            raise ValueError("Use either intermediate nodes or via coordinates in one wire")
        connected = [self.resolve(ref) for ref in (start, end, *through)]
        checked = (
            [connected[0].position, *(point(p) for p in via), connected[1].position]
            if via
            else [node.position for node in connected]
        )
        for first, second in pairwise(checked):
            if first == second:
                raise ValueError("A wire segment cannot have zero length")
        # Sliding window over consecutive vertices; the shorter slices end it.
        for prev, vertex, following in zip(checked, checked[1:], checked[2:], strict=False):
            incoming = (vertex[0] - prev[0], vertex[1] - prev[1])
            outgoing = (following[0] - vertex[0], following[1] - vertex[1])
            cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
            dot = incoming[0] * outgoing[0] + incoming[1] * outgoing[1]
            if abs(cross) <= 1e-12 * hypot(*incoming) * hypot(*outgoing) and dot < 0:
                raise ValueError("A wire cannot double back on itself; list nodes in path order")
        radius = (
            self.corner_radius
            if corner_radius is None
            else nonnegative(corner_radius, "corner_radius")
        )
        cap = self.linecap if linecap is None else self._linecap(linecap)
        join = self.linejoin if linejoin is None else self._linejoin(linejoin)
        commands = self._wire_path(
            checked, radius, set(range(1, len(checked) - 1)) if via else set()
        )
        data = {"from": connected[0].name, "to": connected[-1].name}
        if through:
            data["through"] = " ".join(node.name for node in connected[1:-1])
        group = self.group("wire", id, data=data)
        self.path(group, commands, color=color, linecap=cap, linejoin=join)

    @staticmethod
    def _wire_path(points: list[Point], radius: float, roundable: set[int]) -> list[PathCommand]:
        """Build path commands with circular fillets at routed corners."""
        commands: list[PathCommand] = [("M", *points[0])]
        for index, (prev, vertex, following) in enumerate(
            zip(points, points[1:], points[2:], strict=False), start=1
        ):
            if radius == 0 or index not in roundable:
                commands.append(("L", *vertex))
                continue
            incoming_length = hypot(vertex[0] - prev[0], vertex[1] - prev[1])
            outgoing_length = hypot(following[0] - vertex[0], following[1] - vertex[1])
            incoming = (
                (vertex[0] - prev[0]) / incoming_length,
                (vertex[1] - prev[1]) / incoming_length,
            )
            outgoing = (
                (following[0] - vertex[0]) / outgoing_length,
                (following[1] - vertex[1]) / outgoing_length,
            )
            dot = max(-1.0, min(1.0, incoming[0] * outgoing[0] + incoming[1] * outgoing[1]))
            cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
            if abs(cross) < 1e-12:
                if dot < 0:
                    raise ValueError("A rounded wire cannot reverse direction at a via point")
                commands.append(("L", *vertex))
                continue
            tangent = tan(acos(dot) / 2)
            offset = min(radius * tangent, incoming_length / 2, outgoing_length / 2)
            actual_radius = offset / tangent
            before = (vertex[0] - incoming[0] * offset, vertex[1] - incoming[1] * offset)
            after = (vertex[0] + outgoing[0] * offset, vertex[1] + outgoing[1] * offset)
            commands.append(("L", *before))
            commands.append(("A", actual_radius, actual_radius, 0, 0, int(cross > 0), *after))
        commands.append(("L", *points[-1]))
        return commands

    # ------------------------------------------------------------ decoration

    def box(
        self,
        corner: NodeRef | Point,
        opposite: NodeRef | Point,
        *,
        id: str | None = None,
        color: str | None = None,
        dash: Sequence[float] = (2.2, 1.6),
        corner_radius: float = 2,
        stroke_width: float | None = None,
    ) -> Box:
        """Draw a dashed enclosure, e.g. around a subcircuit that acts as one element.

        The box is decoration only and creates no connection. Pass ``dash=()``
        for a solid outline. Returns the bounds for placing labels.
        """
        first, second = self._position(corner), self._position(opposite)
        if first[0] == second[0] or first[1] == second[1]:
            raise ValueError("A box needs distinct x and y coordinates")
        group = self.group("box", id)
        return self.rect(
            group,
            first,
            second,
            color=color,
            width=0.75 * self.stroke_width if stroke_width is None else stroke_width,
            corner_radius=nonnegative(corner_radius, "corner_radius"),
            dash=dash,
        )

    def label(
        self,
        content: str | Fragment,
        at: NodeRef | Point,
        *,
        id: str | None = None,
        anchor: str = "cc",
        color: str | None = None,
        size: float = 8,
        font_family: str | None = None,
        offset: Point = (0, 0),
    ) -> None:
        """Place plain text or a Vectex-like fragment at an anchored position.

        ``anchor`` combines horizontal ``l/c/r`` and vertical ``t/c/b``.
        Fragments must expose ``width``, ``height``, and ``to_svg()``.
        ``size`` is in circuit user units; ``font_family`` selects the typeface
        for plain text. Fragment typography is set when the fragment is rendered.
        ``color`` (default: the circuit's stroke) colours text, and a fragment
        drawn in ``currentColor``, as VecTeX's are, unless it carries its own.
        """
        x, y = self._position(at)
        dx, dy = point(offset)
        x, y = x + dx, y + dy
        if len(anchor) != 2 or anchor[0] not in "lcr" or anchor[1] not in "tcb":
            raise ValueError("anchor must combine l/c/r with t/c/b")
        group = self.group("label", id)
        ink = color or self.stroke
        group.set("fill", ink)
        if isinstance(content, str):
            attrs = {
                "x": _number(x),
                "y": _number(y),
                "font-size": _number(positive(size, "size")),
                "text-anchor": {"l": "start", "c": "middle", "r": "end"}[anchor[0]],
                "dominant-baseline": {"t": "hanging", "c": "middle", "b": "auto"}[anchor[1]],
            }
            if font_family is not None:
                attrs["font-family"] = font_family
            etree.SubElement(group, _tag("text"), attrs).text = content
            return
        if not isinstance(content, Fragment):
            raise TypeError(
                "label expects text or an SVG fragment with width, height, and to_svg()"
            )
        width, height = (
            positive(content.width, "fragment width"),
            positive(content.height, "fragment height"),
        )
        dx = {"l": 0, "c": -width / 2, "r": -width}[anchor[0]]
        dy = {"t": 0, "c": -height / 2, "b": -height}[anchor[1]]
        group.set("transform", f"translate({_number(x + dx)} {_number(y + dy)})")
        # VecTeX paints its glyphs in currentColor, which follows `color`, not
        # `fill`; a fragment rendered with a colour of its own keeps it.
        group.set("color", ink)
        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
        group.append(deepcopy(etree.fromstring(content.to_svg().encode(), parser=parser)))

    # ------------------------------------------------------------ document

    def to_svg_document(self) -> str:
        """Return a standalone SVG string, also accepted by FigWorks's source protocol."""
        root = deepcopy(self._root)
        root.insert(0, _credit())
        if self._visible_nodes:
            # Connection dots are drawn last so that no wire or symbol covers them.
            by_id = {group.get("id"): group for group in root}
            for group in self._visible_nodes:
                root.append(by_id[group.get("id")])
        return etree.tostring(root, encoding="unicode", pretty_print=True).rstrip("\n") + "\n"

    def write_svg(self, path: str | Path) -> None:
        """Write the standalone SVG document."""
        Path(path).write_text(self.to_svg_document(), encoding="utf-8")


def _credit() -> etree._Element:
    """Dublin Core metadata naming VecWire the document's creator."""
    from vecwire import __version__

    return etree.fromstring(
        '<metadata xmlns="http://www.w3.org/2000/svg">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#">'
        '<cc:Work><dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>'
        "<dc:creator><cc:Agent>"
        f"<dc:title>VecWire v{__version__}, https://github.com/maiani/vecwire</dc:title>"
        "</cc:Agent></dc:creator></cc:Work></rdf:RDF></metadata>"
    )
