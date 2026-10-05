"""Fig. 1(a): a shunted junction circuit, ready to insert in a larger figure.

Run ``python examples/fig1a_cqed.py`` after ``pip install -e .``.
Use ``--tex`` for editable Vectex labels (requires pdflatex and dvisvgm).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cirquit import Circuit

INK = "#262626"
GREY = "#737373"


def make_labels(tex: bool) -> dict[str, object]:
    names = ("C", "L", "VJ", "CJ", "phi", "delta")
    if not tex:
        return dict(zip(names, ("C", "L", "Vⱼ", "Cⱼ", "φ", "δ"), strict=True))

    import vectex

    fragments = vectex.render_many(
        [r"$C$", r"$L$", r"$V_J$", r"$C_J$", r"$\phi$", r"$\delta$"],
        size_pt=8,
        cache_dir=Path(__file__).parent / "output" / ".vectex-cache",
    )
    return dict(zip(names, fragments, strict=True))


def build_circuit(*, tex: bool = False) -> Circuit:
    circuit = Circuit(86, 118, stroke=INK)
    left, branch, top, bottom = 18, 54, 14, 104
    split, join, offset = 60, 88, 8
    junction_x, parasitic_x = branch - offset, branch + offset
    junction_y = (split + join) / 2
    middle = (left + branch) / 2

    circuit.row(top, left_top=left, phi=middle, right_top=branch, dots={"phi"})
    circuit.row(bottom, left_bottom=left, ground_node=middle, right_bottom=branch)
    circuit.column(branch, coil_top=20, coil_bottom=44, delta=52, dots={"delta"})
    circuit.column(branch, split_center=split, join_center=join)
    circuit.column(junction_x, junction_top=split, junction_bottom=join)
    circuit.column(parasitic_x, parasitic_top=split, parasitic_bottom=join)

    # The shunt C shares the upper and lower rails with the L-(V_J || C_J) branch.
    circuit.wire("left_top", "phi", "right_top", id="upper-rail")
    circuit.wire("left_bottom", "ground_node", "right_bottom", id="lower-rail")
    circuit.capacitor("left_top", "left_bottom", id="shunt-C")
    circuit.ground("ground_node", id="ground")

    circuit.wire("right_top", "coil_top", id="upper-lead")
    circuit.inductor("coil_top", "coil_bottom", id="L")
    circuit.wire("coil_bottom", "delta", "split_center", id="internal-lead")
    circuit.wire("junction_top", "split_center", "parasitic_top", id="parallel-top")
    circuit.wire("junction_bottom", "join_center", "parasitic_bottom", id="parallel-bottom")
    circuit.junction("junction_top", "junction_bottom", id="VJ")
    circuit.capacitor(
        "parasitic_top",
        "parasitic_bottom",
        id="CJ",
        plate_width=9,
        gap=3.6,
        color=GREY,
    )
    circuit.wire("join_center", "right_bottom", id="lower-lead")

    labels = make_labels(tex)
    circuit.label(labels["C"], (left - 9.5, (top + bottom) / 2), id="label-C", anchor="rc")
    circuit.label(labels["L"], (branch + 7.5, 32), id="label-L", anchor="lc")
    circuit.label(labels["VJ"], (junction_x - 5.5, junction_y), id="label-VJ", anchor="rc")
    circuit.label(
        labels["CJ"], (parasitic_x + 6.5, junction_y), id="label-CJ", anchor="lc", color=GREY
    )
    circuit.label(labels["phi"], "phi", offset=(0, -3), id="label-phi", anchor="cb")
    circuit.label(labels["delta"], "delta", offset=(-4, 0), id="label-delta", anchor="rc")
    return circuit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tex", action="store_true", help="render editable Vectex labels")
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).parent / "output" / "fig1a.svg"
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    build_circuit(tex=args.tex).write_svg(args.output)
    print(args.output)
