"""Build the picture at the top of the README.

It is the circuit-QED example, ``examples/fig1a_cqed.py``, with its labels
typeset by VecTeX, on a white rectangle so it reads on a dark page too.  Needs
the ``tex`` extra and a TeX installation, as ``--tex`` does.

Usage:
    python docs/readme_figure.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from fig1a_cqed import build_circuit  # noqa: E402

OUT = ROOT / "docs" / "images" / "readme.svg"
SVG = "http://www.w3.org/2000/svg"


def on_white(document: str) -> str:
    """The document with an opaque white rectangle under its content."""
    root = etree.fromstring(document.encode("utf-8"))
    x, y, w, h = (float(v) for v in root.get("viewBox", "").replace(",", " ").split())
    rect = etree.Element(
        f"{{{SVG}}}rect", x=f"{x:g}", y=f"{y:g}", width=f"{w:g}", height=f"{h:g}", fill="#ffffff"
    )
    rect.set("id", "background")
    root.insert(0, rect)
    return etree.tostring(root, encoding="unicode") + "\n"


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(on_white(build_circuit(tex=True).to_svg_document()), encoding="utf-8")
    print(f"wrote {OUT}")
