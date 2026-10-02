"""Harmonic junction symbols and a multiharmonic junction.

Top row: the bare X is the standard Josephson-junction symbol, which leaves the
current-phase relation unspecified. The boxed symbols each show one tunnelling
harmonic: a square crossed by ``m`` diagonals each way is a ``cos(m phi)``
term, in which ``m`` Cooper pairs tunnel together; two dots mark the odd
``sin(phi)`` term of a phi0 junction. The ``m = 1`` box is the bare X in a square.
Bottom: an inductor in series with a sinusoidal junction (dashed box) acts on
the outer phase like a multiharmonic junction ``cos phi + cos 2phi + ...``.

Run ``python examples/harmonic_junctions.py`` after ``pip install -e .``.
Use ``--tex`` for editable Vectex labels (requires pdflatex and dvisvgm).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cirquit import Circuit

INK = "#262626"
SHADES = ("#4a3aa7", "#8075c1", "#a59dd3")  # orders m = 1, 2, 3 in one hue
SINE = "#1baf7a"

# name, harmonic order (None: the bare X), kind, colour, plain label, TeX label
LEGEND = (
    ("bare", None, "cos", INK, "JJ", r"$\mathrm{JJ}$"),
    ("cos1", 1, "cos", SHADES[0], "cos φ", r"$\cos\phi$"),
    ("cos2", 2, "cos", SHADES[1], "cos 2φ", r"$\cos 2\phi$"),
    ("cos3", 3, "cos", SHADES[2], "cos 3φ", r"$\cos 3\phi$"),
    ("sin1", 1, "sin", SINE, "sin φ", r"$\sin\phi$"),
)


def make_labels(tex: bool) -> dict[str, object]:
    names = [name for name, *_ in LEGEND] + ["L", "approx"]
    if not tex:
        return dict(zip(names, [text for *_, text, _ in LEGEND] + ["L", "≃"]))

    import vectex

    fragments = vectex.render_many(
        [source for *_, source in LEGEND] + [r"$L$", r"$\simeq$"],
        size_pt=8,
        cache_dir=Path(__file__).parent / "output" / ".vectex-cache",
    )
    return dict(zip(names, fragments))


def build_circuit(*, tex: bool = False) -> Circuit:
    circuit = Circuit(206, 112, stroke=INK)
    labels = make_labels(tex)

    for index, (name, order, kind, color, *_) in enumerate(LEGEND):
        x = 12 + 40 * index
        top, bottom = f"{name}_top", f"{name}_bottom"
        circuit.column(x, **{top: 6, bottom: 30})
        style = {"id": f"legend-{name}", "size": 9, "color": color, "lead_color": INK}
        if order is None:
            circuit.junction(top, bottom, **style)
        else:
            circuit.harmonic_junction(top, bottom, order, kind=kind, **style)
        circuit.label(labels[name], (x + 7, 18), id=f"label-{name}", anchor="lc", size=7)

    # The relation below is centred on the wider legend.
    dx = 15

    # Left of the relation: L in series with a sinusoidal junction.
    circuit.column(dx + 24, branch_top=44, coil_top=50, coil_bottom=70, branch_bottom=106)
    circuit.wire("branch_top", "coil_top", id="series-upper-lead")
    circuit.inductor("coil_top", "coil_bottom", id="series-L")
    circuit.harmonic_junction(
        "coil_bottom",
        "branch_bottom",
        1,
        id="series-JJ",
        size=9,
        color=SHADES[0],
        lead_color=INK,
    )
    enclosure = circuit.box((dx + 12, 47), (dx + 42, 102), id="series-branch")
    circuit.label(labels["L"], (dx + 31, 60), id="label-L", anchor="lc")
    circuit.label(labels["approx"], (enclosure.right + 10, 75), id="label-approx", size=10)

    # Right of the relation: the multiharmonic junction it acts like.
    circuit.column(dx + 118, sum_top=44, sum_bottom=106)
    circuit.harmonic_sum(
        "sum_top", "sum_bottom", (1, 2, 3), id="multiharmonic", colors=SHADES, size=9
    )
    return circuit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tex", action="store_true", help="render editable Vectex labels")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "output" / "harmonic_junctions.svg",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    build_circuit(tex=args.tex).write_svg(args.output)
    print(args.output)
