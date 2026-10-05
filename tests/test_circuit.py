from __future__ import annotations

import runpy
from pathlib import Path

import pytest
from lxml import etree

from vecwire import Circuit

NS = {"s": "http://www.w3.org/2000/svg"}


def test_fig1a_has_named_editable_components_and_stable_output():
    build_circuit = runpy.run_path(str(Path(__file__).parents[1] / "examples" / "fig1a_cqed.py"))[
        "build_circuit"
    ]
    circuit = build_circuit()
    svg = circuit.to_svg_document()
    root = etree.fromstring(svg.encode())
    assert root.get("viewBox") == "0 0 86 118"
    assert root.get("width") == "86pt"
    assert svg == circuit.to_svg_document()
    assert root.xpath('count(//s:g[@data-component="capacitor"])', namespaces=NS) == 2
    assert root.xpath('count(//s:g[@data-component="josephson-junction"])', namespaces=NS) == 1
    assert root.xpath('count(//s:g[@data-component="node"])', namespaces=NS) == 15
    assert root.xpath('count(//s:g[@data-component="node"]/s:circle)', namespaces=NS) == 2
    ids = root.xpath("//s:g/@id", namespaces=NS)
    assert len(ids) == len(set(ids))
    assert {"shunt-C", "L", "VJ", "CJ", "phi", "delta"} <= set(ids)
    rail = root.xpath('//s:g[@id="upper-rail"]', namespaces=NS)[0]
    assert rail.get("data-from") == "left_top"
    assert rail.get("data-through") == "phi"
    assert rail.get("data-to") == "right_top"


def test_components_include_leads_and_support_rotation():
    circuit = Circuit(60, 40)
    cap_left = circuit.node("cap-left", (5, 10))
    cap_right = circuit.node("cap-right", (45, 10))
    coil_top = circuit.node("coil-top", (50, 5))
    coil_bottom = circuit.node("coil-bottom", (50, 35))
    jj_left = circuit.node("jj-left", (5, 25))
    jj_right = circuit.node("jj-right", (35, 25))
    circuit.capacitor(cap_left, cap_right, id="horizontal-capacitor")
    circuit.inductor(coil_top, coil_bottom, id="vertical-inductor")
    circuit.junction(jj_left, jj_right, id="horizontal-junction")
    root = etree.fromstring(circuit.to_svg_document().encode())
    plates = root.xpath('//s:g[@id="horizontal-capacitor"]/s:line[position()>2]', namespaces=NS)
    assert len(plates) == 2
    assert all(plate.get("x1") == plate.get("x2") for plate in plates)
    assert root.xpath('//s:g[@id="vertical-inductor"]/s:path', namespaces=NS)
    assert len(root.xpath('//s:g[@id="horizontal-junction"]/s:line', namespaces=NS)) == 4


def test_invalid_geometry_and_duplicate_ids_are_rejected():
    circuit = Circuit(20, 20)
    a = circuit.node("a", (0, 0))
    b = circuit.node("b", (5, 5))
    near = circuit.node("near", (0, 2))
    with pytest.raises(ValueError, match="horizontal or vertical"):
        circuit.capacitor(a, b)
    with pytest.raises(ValueError, match="gap"):
        circuit.capacitor(a, near, gap=2)
    circuit.node("same", (1, 1))
    with pytest.raises(ValueError, match="Duplicate"):
        circuit.node("same", (2, 2))
    other = Circuit(20, 20).node("foreign", (1, 1))
    with pytest.raises(ValueError, match="created by this Circuit"):
        circuit.wire(a, other)


def test_routed_wire_uses_one_path_with_roundable_joints():
    circuit = Circuit(30, 30, linecap="round", linejoin="round", corner_radius=3)
    start = circuit.node("start", (0, 0))
    end = circuit.node("end", (10, 10))
    circuit.wire(start, end, via=((10, 0),), id="route")
    root = etree.fromstring(circuit.to_svg_document().encode())
    group = root.xpath('//s:g[@id="route"]', namespaces=NS)[0]
    path = group.xpath("./s:path", namespaces=NS)[0]
    assert group.get("data-from") == "start"
    assert group.get("data-to") == "end"
    assert path.get("d") == "M 0 0 L 7 0 A 3 3 0 0 1 10 3 L 10 10"
    assert path.get("stroke-linejoin") == "round"
    assert path.get("stroke-linecap") == "round"
    circuit.wire(
        start, end, via=((0, 10),), id="sharp", corner_radius=0, linecap="butt", linejoin="bevel"
    )
    sharp = etree.fromstring(circuit.to_svg_document().encode()).xpath(
        '//s:g[@id="sharp"]/s:path', namespaces=NS
    )[0]
    assert " A " not in sharp.get("d")
    assert sharp.get("stroke-linejoin") == "bevel"
    assert sharp.get("stroke-linecap") == "butt"


def test_node_shortcuts_and_connected_waypoints_stay_on_wire():
    circuit = Circuit(30, 30, corner_radius=3)
    circuit.row(0, left=0, bend=10)
    circuit.column(10, end=10)
    circuit.wire("left", "bend", "end", id="chain")
    root = etree.fromstring(circuit.to_svg_document().encode())
    chain = root.xpath('//s:g[@id="chain"]', namespaces=NS)[0]
    assert chain.get("data-through") == "bend"
    assert chain.xpath("./s:path", namespaces=NS)[0].get("d") == "M 0 0 L 10 0 L 10 10"
    with pytest.raises(ValueError, match="Unknown node"):
        circuit.wire("left", "missing")
    with pytest.raises(ValueError, match="either intermediate nodes or via"):
        circuit.wire("left", "bend", "end", via=((5, 5),))


def test_fragment_label_is_embedded_and_positioned():
    class Fragment:
        width = 10
        height = 4

        def to_svg(self):
            return '<g xmlns="http://www.w3.org/2000/svg"><path d="M 0 0 L 10 4"/></g>'

    circuit = Circuit(30, 30)
    circuit.label(Fragment(), (15, 10), id="tex-label", anchor="cc")
    root = etree.fromstring(circuit.to_svg_document().encode())
    group = root.xpath('//s:g[@id="tex-label"]', namespaces=NS)[0]
    assert group.get("transform") == "translate(10 8)"
    assert group.xpath(".//s:path", namespaces=NS)


def test_label_rejects_an_object_that_is_not_a_fragment():
    class Sized:
        width = 10
        height = 4

    with pytest.raises(TypeError, match="width, height, and to_svg"):
        Circuit(30, 30).label(Sized(), (15, 10))  # type: ignore[arg-type]


def _root(circuit: Circuit):
    return etree.fromstring(circuit.to_svg_document().encode())


def test_harmonic_junction_draws_boxed_crosses_per_order():
    circuit = Circuit(80, 40)
    for index, (order, kind) in enumerate(((1, "cos"), (2, "cos"), (3, "cos"), (1, "sin"))):
        circuit.column(10 + 20 * index, **{f"t{index}": 4, f"b{index}": 34})
        circuit.harmonic_junction(
            f"t{index}",
            f"b{index}",
            order,
            id=f"jj{index}",
            kind=kind,
            color="#4a3aa7",
            lead_color="#262626",
        )
    root = _root(circuit)
    for index, order in enumerate((1, 2, 3, 1)):
        group = root.xpath(f'//s:g[@id="jj{index}"]', namespaces=NS)[0]
        assert group.get("data-component") == "josephson-junction"
        assert group.get("data-harmonic") == str(order)
        assert len(group.xpath("./s:rect", namespaces=NS)) == 1
        lines = group.xpath("./s:line", namespaces=NS)
        assert len(lines) == 2 + 2 * order  # two leads plus m diagonals each way
        assert [line.get("stroke") for line in lines[:2]] == ["#262626"] * 2
        assert {line.get("stroke") for line in lines[2:]} == {"#4a3aa7"}
    sine = root.xpath('//s:g[@id="jj3"]', namespaces=NS)[0]
    assert sine.get("data-kind") == "sin"
    assert len(sine.xpath("./s:circle", namespaces=NS)) == 2


def test_harmonic_diagonals_stay_inside_the_square():
    circuit = Circuit(40, 40)
    circuit.column(20, top=2, bottom=38)
    circuit.harmonic_junction("top", "bottom", 4, id="jj", size=10)
    group = _root(circuit).xpath('//s:g[@id="jj"]', namespaces=NS)[0]
    for line in group.xpath("./s:line", namespaces=NS)[2:]:
        for key in ("x1", "x2", "y1", "y2"):
            assert 15 - 1e-9 <= float(line.get(key)) <= 25 + 1e-9


def test_plain_junction_is_unchanged_and_kinds_are_validated():
    circuit = Circuit(40, 40)
    circuit.column(20, top=2, bottom=38)
    circuit.junction("top", "bottom", id="plain")
    group = _root(circuit).xpath('//s:g[@id="plain"]', namespaces=NS)[0]
    assert group.get("data-harmonic") is None
    assert not group.xpath("./s:rect", namespaces=NS)
    with pytest.raises(ValueError, match="order"):
        circuit.harmonic_junction("top", "bottom", 0)
    with pytest.raises(ValueError, match="kind"):
        circuit.harmonic_junction("top", "bottom", kind="tan")
    implied = Circuit(40, 40)
    implied.column(20, top=2, bottom=38)
    implied.harmonic_junction("top", "bottom", id="sine", kind="sin")
    sine = _root(implied).xpath('//s:g[@id="sine"]', namespaces=NS)[0]
    assert sine.get("data-harmonic") == "1"


def test_harmonic_sum_reads_left_to_right_on_a_vertical_branch():
    circuit = Circuit(120, 80)
    circuit.column(60, top=4, bottom=76)
    box = circuit.harmonic_sum(
        "top", "bottom", (1, 2, 3), id="multi", colors=("#111111", "#555555", "#999999")
    )
    root = _root(circuit)
    group = root.xpath('//s:g[@id="multi"]', namespaces=NS)[0]
    assert group.get("data-component") == "harmonic-sum"
    assert group.get("data-orders") == "1 2 3"
    terms = group.xpath('./s:g[@data-component="josephson-junction"]', namespaces=NS)
    assert [term.get("id") for term in terms] == ["multi-m1", "multi-m2", "multi-m3"]
    assert [term.get("data-harmonic") for term in terms] == ["1", "2", "3"]
    assert len(group.xpath('./s:g[@data-component="plus"]', namespaces=NS)) == 3
    assert len(group.xpath('./s:g[@data-component="ellipsis"]/s:circle', namespaces=NS)) == 3
    outline = group.xpath("./s:rect[@stroke-dasharray]", namespaces=NS)
    assert len(outline) == 1
    xs = [x for x, _ in box.terms]
    assert xs == sorted(xs) and len({y for _, y in box.terms}) == 1
    assert box.left < xs[0] and xs[-1] < box.right
    assert box.at("cc") == box.center
    assert box.center == pytest.approx((60, 40))  # centred on the branch


def _floats(line, *keys):
    return [float(line.get(key)) for key in keys]


def test_harmonic_sum_terms_hang_between_rails_joined_to_the_branch():
    circuit = Circuit(120, 80)
    circuit.column(60, top=4, bottom=76)
    box = circuit.harmonic_sum("top", "bottom", (1, 2, 3), id="multi")
    group = _root(circuit).xpath('//s:g[@id="multi"]', namespaces=NS)[0]
    rails = {}
    for side in ("top", "bottom"):
        rail = group.xpath(f'./s:g[@id="multi-rail-{side}"]/s:line', namespaces=NS)[0]
        x1, y1, x2, y2 = _floats(rail, "x1", "y1", "x2", "y2")
        assert y1 == y2 and box.top < y1 < box.bottom and box.left < x1 < x2 < box.right
        rails[side] = (min(x1, x2), max(x1, x2), y1)
    # Branch leads run from the terminals to the rails on the branch axis.
    upper, lower = group.xpath("./s:line", namespaces=NS)
    assert _floats(upper, "x1", "y1", "x2") == [60, 4, 60]
    assert float(upper.get("y2")) == pytest.approx(rails["top"][2])
    assert _floats(lower, "x2", "y2", "x1") == [60, 76, 60]
    assert float(lower.get("y1")) == pytest.approx(rails["bottom"][2])
    assert all(left < 60 < right for left, right, _ in rails.values())
    # Every term touches both rails, and no terminal dots are drawn.
    for term in group.xpath('./s:g[@data-component="josephson-junction"]', namespaces=NS):
        assert not term.xpath("./s:circle", namespaces=NS)
        tips = [_floats(line, "x2", "y2") for line in term.xpath("./s:line", namespaces=NS)[:2]]
        for (x, y), side in zip(tips, ("top", "bottom"), strict=True):
            left, right, rail_y = rails[side]
            assert y == pytest.approx(rail_y) and left <= x <= right


def test_harmonic_sum_dot_notation_keeps_leads_at_the_box():
    circuit = Circuit(120, 80)
    circuit.column(60, top=4, bottom=76)
    box = circuit.harmonic_sum("top", "bottom", (1, 2), id="dots", rails=False)
    group = _root(circuit).xpath('//s:g[@id="dots"]', namespaces=NS)[0]
    assert not group.xpath('./s:g[@data-component="rail"]', namespaces=NS)
    leads = group.xpath("./s:line", namespaces=NS)
    assert float(leads[0].get("y2")) == pytest.approx(box.top)
    assert float(leads[1].get("y1")) == pytest.approx(box.bottom)
    assert len(group.xpath(".//s:g[@data-harmonic]/s:circle", namespaces=NS)) == 4


def test_harmonic_sum_stacks_top_to_bottom_on_a_horizontal_branch():
    circuit = Circuit(120, 120)
    circuit.row(60, left=4, right=116)
    box = circuit.harmonic_sum("left", "right", (1, 2), ellipsis=False, kinds=("cos", "sin"))
    ys = [y for _, y in box.terms]
    assert ys == sorted(ys) and len({x for x, _ in box.terms}) == 1
    root = _root(circuit)
    assert not root.xpath('//s:g[@data-component="ellipsis"]', namespaces=NS)
    assert len(root.xpath('//s:g[@data-component="plus"]', namespaces=NS)) == 1
    with pytest.raises(ValueError, match="match the number"):
        circuit.harmonic_sum("left", "right", (1, 2), colors=("#000000",))
    short = Circuit(40, 40)
    short.column(20, top=10, bottom=20)
    with pytest.raises(ValueError, match="shorter"):
        short.harmonic_sum("top", "bottom")


def test_box_is_dashed_decoration_with_label_anchors():
    circuit = Circuit(60, 60)
    circuit.node("corner", (40, 50))
    box = circuit.box((10, 5), "corner", id="branch", corner_radius=3)
    rect = _root(circuit).xpath('//s:g[@id="branch"]/s:rect', namespaces=NS)[0]
    assert (rect.get("x"), rect.get("y"), rect.get("width"), rect.get("height")) == (
        "10",
        "5",
        "30",
        "45",
    )
    assert rect.get("stroke-dasharray") == "2.2 1.6"
    assert rect.get("rx") == "3"
    assert box.at("rt") == (40, 5) and box.at("lb") == (10, 50)
    circuit.box((0, 0), (5, 5), id="solid", dash=())
    solid = _root(circuit).xpath('//s:g[@id="solid"]/s:rect', namespaces=NS)[0]
    assert solid.get("stroke-dasharray") is None
    with pytest.raises(ValueError, match="distinct"):
        circuit.box((0, 0), (0, 5))
    with pytest.raises(ValueError, match="anchor"):
        box.at("xx")


def test_wire_rejects_out_of_order_nodes():
    circuit = Circuit(30, 10)
    circuit.row(5, left=0, middle=10, right=20)
    with pytest.raises(ValueError, match="path order"):
        circuit.wire("left", "right", "middle")
    circuit.wire("left", "middle", "right", id="rail")


def test_harmonic_example_is_deterministic():
    build_circuit = runpy.run_path(
        str(Path(__file__).parents[1] / "examples" / "harmonic_junctions.py")
    )["build_circuit"]
    svg = build_circuit().to_svg_document()
    assert svg == build_circuit().to_svg_document()
    root = etree.fromstring(svg.encode())
    assert root.xpath('count(//s:g[@data-component="harmonic-sum"])', namespaces=NS) == 1
    assert root.xpath('count(//s:g[@data-component="box"])', namespaces=NS) == 1
    bare = root.xpath('//s:g[@id="legend-bare"]', namespaces=NS)[0]
    assert bare.get("data-harmonic") is None and not bare.xpath("./s:rect", namespaces=NS)
    boxed = root.xpath('//s:g[starts-with(@id, "legend-")][@data-harmonic]', namespaces=NS)
    assert [(g.get("data-harmonic"), g.get("data-kind")) for g in boxed] == [
        ("1", "cos"),
        ("2", "cos"),
        ("3", "cos"),
        ("1", "sin"),
    ]
