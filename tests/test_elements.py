"""The symbol library and its boundary with the core canvas."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from lxml import etree

import cirquit
from cirquit import Branch, Circuit, elements

NS = {"s": "http://www.w3.org/2000/svg"}
ELEMENTS_DIR = Path(cirquit.__file__).parent / "elements"


def _root(circuit: Circuit):
    return etree.fromstring(circuit.to_svg_document().encode())


def _group(circuit: Circuit, id: str):
    return _root(circuit).xpath(f'//s:g[@id="{id}"]', namespaces=NS)[0]


def _segments(group, xpath="./s:line"):
    return [
        tuple(float(line.get(key)) for key in ("x1", "y1", "x2", "y2"))
        for line in group.xpath(xpath, namespaces=NS)
    ]


def _undirected(group):
    return sorted(tuple(sorted((s[:2], s[2:]))) for s in _segments(group))


def _vertical():
    circuit = Circuit(40, 40)
    circuit.column(20, top=2, bottom=38)
    return circuit


# ------------------------------------------------------------ bare and boxed junctions


def test_bare_junction_is_just_the_x():
    circuit = _vertical()
    circuit.junction("top", "bottom", id="jj", size=8, color="#aa0000", lead_color="#000000")
    group = _group(circuit, "jj")
    assert group.get("data-component") == "josephson-junction"
    assert group.get("data-harmonic") is None and group.get("data-kind") is None
    assert not group.xpath("./s:rect | ./s:circle", namespaces=NS)
    leads, cross = _segments(group)[:2], _segments(group)[2:]
    assert leads == [(20, 2, 20, 16), (20, 24, 20, 38)]
    # Two strokes along the diagonals of the 8 x 8 square centred at (20, 20).
    assert sorted(cross) == [(16, 16, 24, 24), (24, 16, 16, 24)]
    colors = [line.get("stroke") for line in group.xpath("./s:line", namespaces=NS)]
    assert colors == ["#000000", "#000000", "#aa0000", "#aa0000"]


def test_boxed_first_harmonic_is_the_bare_x_in_a_square():
    bare, boxed = _vertical(), _vertical()
    bare.junction("top", "bottom", id="jj", size=8)
    boxed.harmonic_junction("top", "bottom", 1, id="jj", size=8)
    bare_group, boxed_group = _group(bare, "jj"), _group(boxed, "jj")
    assert _undirected(boxed_group) == _undirected(bare_group)  # same leads and X strokes
    rect = boxed_group.xpath("./s:rect", namespaces=NS)[0]
    assert [rect.get(key) for key in ("x", "y", "width", "height")] == ["16", "16", "8", "8"]
    assert (boxed_group.get("data-harmonic"), boxed_group.get("data-kind")) == ("1", "cos")


@pytest.mark.parametrize("order", [1, 2, 3, 5])
def test_boxed_junction_has_order_diagonals_each_way(order):
    circuit = _vertical()
    circuit.harmonic_junction("top", "bottom", order, id="jj")
    group = _group(circuit, "jj")
    diagonals = _segments(group)[2:]
    rising = [s for s in diagonals if (s[2] - s[0]) * (s[3] - s[1]) < 0]
    assert len(diagonals) == 2 * order and len(rising) == order
    assert not group.xpath("./s:circle", namespaces=NS)


def test_sine_kind_adds_two_dots_and_is_validated():
    circuit = _vertical()
    circuit.harmonic_junction("top", "bottom", kind="sin", id="jj")
    group = _group(circuit, "jj")
    assert group.get("data-kind") == "sin"
    assert len(group.xpath("./s:circle", namespaces=NS)) == 2
    with pytest.raises(ValueError, match="kind"):
        circuit.harmonic_junction("top", "bottom", kind="sinh")
    with pytest.raises(ValueError, match="order"):
        circuit.harmonic_junction("top", "bottom", True)
    with pytest.raises(ValueError, match="shorter"):
        circuit.junction("top", "bottom", size=40)


def test_harmonic_sum_terms_are_the_boxed_glyph():
    single, summed = Circuit(120, 80), Circuit(120, 80)
    single.column(60, top=4, bottom=76)
    summed.column(60, top=4, bottom=76)
    single.harmonic_junction("top", "bottom", 2, id="jj", size=9, color="#123456")
    box = summed.harmonic_sum("top", "bottom", (2,), id="sum", size=9, colors="#123456")

    def relative(group, centre):
        lines = _segments(group)[2:]  # skip the leads
        return sorted(
            tuple(round(v - c, 9) for v, c in zip(seg, centre * 2, strict=True)) for seg in lines
        )

    term = _group(summed, "sum-m2")
    assert relative(term, box.terms[0]) == relative(_group(single, "jj"), (60.0, 40.0))


# ------------------------------------------------------------ the core/elements split


def test_library_functions_and_circuit_methods_draw_the_same_document():
    def draw(use_methods: bool) -> str:
        circuit = Circuit(80, 60)
        circuit.row(5, a=5, b=75)
        circuit.row(55, c=5, d=75)
        circuit.column(40, e=10, f=50)
        calls = [
            ("capacitor", ("a", "c"), {"id": "C"}),
            ("inductor", ("b", "d"), {"id": "L", "turns": 3}),
            ("junction", ("e", "f"), {"id": "X"}),
            ("ground", ("d",), {"id": "G"}),
        ]
        for name, args, kwargs in calls:
            if use_methods:
                getattr(circuit, name)(*args, **kwargs)
            else:
                getattr(elements, name)(circuit, *args, **kwargs)
        return circuit.to_svg_document()

    assert draw(use_methods=True) == draw(use_methods=False)


def resistor(circuit: Circuit, start, end, *, id=None, zigzags=3, color=None):
    """A symbol defined outside cirquit, written against the public drawing API only."""
    branch = circuit.branch(start, end)
    group = circuit.group("resistor", id, branch=branch, data={"zigzags": zigzags})
    lead = branch.length / 4
    step = (branch.length - 2 * lead) / (2 * zigzags)
    commands = [("M", *branch.start.position), ("L", *branch.at(lead))]
    for index in range(2 * zigzags):
        commands.append(("L", *branch.at(lead + (index + 0.5) * step, 3 * (-1) ** index)))
    commands += [("L", *branch.at(branch.length - lead)), ("L", *branch.end.position)]
    circuit.path(group, commands, color=color)


def test_a_new_symbol_needs_no_change_to_the_core():
    circuit = Circuit(60, 60)
    circuit.row(10, left=0, right=40)
    circuit.column(50, top=0, bottom=40)
    resistor(circuit, "left", "right", id="R1")
    resistor(circuit, "top", "bottom", id="R2", zigzags=2)
    root = _root(circuit)
    first = root.xpath('//s:g[@id="R1"]', namespaces=NS)[0]
    assert (first.get("data-component"), first.get("data-from"), first.get("data-to")) == (
        "resistor",
        "left",
        "right",
    )
    assert first.get("data-zigzags") == "3"
    d = first.xpath("./s:path", namespaces=NS)[0].get("d")
    assert d.startswith("M 0 10 L 10 10 L 11.6666666667 13 ") and d.endswith("L 40 10")
    vertical = root.xpath('//s:g[@id="R2"]/s:path', namespaces=NS)[0].get("d")
    assert vertical.startswith("M 50 0 L 50 10 L 47 12.5 ")  # same symbol, rotated
    assert circuit.to_svg_document() == circuit.to_svg_document()
    with pytest.raises(ValueError, match="Duplicate"):
        resistor(circuit, "left", "right", id="R1")
    with pytest.raises(ValueError, match="horizontal or vertical"):
        resistor(circuit, "left", "bottom")


def test_branch_coordinates_follow_the_terminal_order():
    circuit = Circuit(20, 20)
    a, b = circuit.node("a", (2, 5)), circuit.node("b", (12, 5))
    forward, backward = circuit.branch(a, b), Branch(b, a)
    assert forward.length == 10 and forward.direction == (1, 0)
    assert forward.at(4, 1) == (6, 6)
    assert backward.at(4, 1) == (8, 4)
    with pytest.raises(ValueError, match="distinct"):
        circuit.branch(a, a)


def _runtime_imports(tree: ast.Module):
    """Imports outside ``if TYPE_CHECKING:`` blocks."""
    for node in tree.body:
        if isinstance(node, ast.If) and getattr(node.test, "id", None) == "TYPE_CHECKING":
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.ImportFrom):
                yield child


@pytest.mark.parametrize("path", sorted(ELEMENTS_DIR.glob("*.py")), ids=lambda path: path.name)
def test_elements_use_only_the_public_api(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and getattr(node.value, "id", None) == "circuit":
            assert not node.attr.startswith("_"), f"circuit.{node.attr} is private"
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                assert not alias.name.startswith("_"), f"imports private {alias.name}"
    for node in _runtime_imports(tree):
        # The core imports the library to bind its methods, so never the reverse.
        assert node.module != "core", f"{path.name} imports cirquit.core at runtime"
