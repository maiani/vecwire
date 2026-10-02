# cirquit

Cirquit draws editable SVG schematics for electrical circuits, with circuit-QED
figures as the first use case. The API covers wires, capacitors,
inductors, Josephson junctions (the bare X, boxed harmonic junctions, and
multiharmonic junctions), ground symbols, connection nodes, dashed enclosures, and labels.
Components connect named, positioned nodes, include their own leads, and become
named SVG groups when given an `id`.

The first example reproduces the circuit sketch in Fig. 1(a) of the supplied
reference: shunt capacitance `C` across an inductor `L` in series with the
parallel `V_J` and `C_J` junction branch. It marks the node phases `φ` and `δ`.
The generated [SVG preview](examples/fig1a.svg) is included in the repository.

## Install and run

```bash
python -m pip install -e .
python examples/fig1a_cqed.py
```

The example writes `examples/output/fig1a.svg`. For publication labels that
remain editable through TexText, install the optional Vectex dependency and
run the example with `--tex`:

```bash
python -m pip install -e '.[tex]'
python examples/fig1a_cqed.py --tex
```

Vectex also needs `pdflatex` and `dvisvgm` on `PATH`. The default example uses
plain SVG text and runs without a TeX installation.

## Drawing API

```python
from cirquit import Circuit

circuit = Circuit(width=86, height=118, linecap="round", linejoin="round")
circuit.row(14, top_left=18, phi=36, top_right=54, dots={"phi"})
circuit.column(18, bottom_left=104)
circuit.column(54, coil_top=20, coil_bottom=44)
circuit.wire("top_left", "phi", "top_right")
circuit.capacitor("top_left", "bottom_left", id="shunt-C")
circuit.wire("top_right", "coil_top")
circuit.inductor("coil_top", "coil_bottom", id="L")
circuit.label("φ", "phi", offset=(0, -3), anchor="cb")
circuit.write_svg("circuit.svg")
```

Two-terminal symbols support horizontal and vertical placement. A `Node` is a
placed connection point; wires join nodes into an electrical net. A wire
visits its nodes in the order given, and a route that doubles back is rejected.
Merely crossing or overlapping in the drawing does not establish a connection.
Methods accept
node names or the `Node` values returned by `node()` and `nodes()`. A wire can
pass through several connected nodes. Optional `via` coordinates shape a route
between two nodes without creating additional connections:

```python
circuit.wire("phi", "coil_bottom", via=((36, 32), (54, 32)), corner_radius=2)
```

`row()` and `column()` are shortcuts for declaring several positioned nodes
that share one coordinate. They do not draw wires; `nodes()` accepts arbitrary
positions when a row or column is not convenient.

`Circuit` accepts `linecap`, `linejoin`, and a default `corner_radius` for wire
routes. Each `wire` can override them. `linejoin="round"` softens the stroke at
an angular bend; `corner_radius` curves the wire centerline. Routed wires are
single SVG paths so both controls affect the rendered result. A path through a
named node passes through that position exactly, even when a corner radius is
set. Labels accept
plain text or a Vectex fragment; a fragment's SVG group is embedded in the
output. `to_svg_document()`
returns a standalone SVG string and is the only interface needed to place a
`Circuit` in a FigForge panel:

```python
from figforge import Figure

figure = Figure(width="100mm", height="60mm")
figure.panel("schematic", x=0, y=0, w="45mm", h="60mm").add(circuit, id="circuit")
```

The `Circuit` records drawing geometry. It does not infer electrical topology
or compute circuit parameters from the SVG; those remain in the scientific
model that produces the figure.

## Josephson junctions

There are two junction symbols. `junction()` draws the bare X, the standard
Josephson-junction symbol, which leaves the current-phase relation
unspecified. `harmonic_junction()` draws the boxed symbol of one tunnelling
harmonic. Its square holds `order` crossed diagonals each way for a `cos(mφ)`
term, in which `m` Cooper pairs tunnel together. `kind="sin"` adds two dots
for the odd `sin(mφ)` term of a φ0 junction. The `m = 1` box is the bare X
inside its square, so the two symbols line up in one figure. In both, `color`
sets the glyph and `lead_color` keeps the leads in the circuit ink.

```python
circuit.junction("top", "bottom", id="JJ")  # bare X
circuit.harmonic_junction("top", "bottom", 2, color="#8075c1", lead_color="#262626")
circuit.harmonic_junction("top", "bottom", kind="sin")  # sin φ, m = 1
```

Both groups have `data-component="josephson-junction"`. The boxed one also
records `data-harmonic` and `data-kind`, so a stylesheet or a FigForge
selector can tell the two apart.

`harmonic_sum()` builds a multiharmonic junction from the same boxed glyph. It
draws a dashed box holding `⊠ + ⊠⊠ + ⊠⊠⊠ + ⋯` between two terminals. The
harmonics of one junction add as energies, so the terms are drawn in
parallel: each hangs between two rails, and the branch leads join the rails at
the centre of the box. `rails=False` ends each term in terminal dots instead,
a shorthand sum notation. The sum reads left to right on a vertical branch
and top to bottom on a horizontal one. `colors` and `kinds` set each term, and
`ellipsis=False` drops the trailing `+ ⋯`.

`box()` draws a dashed enclosure around a subcircuit that acts as one element.
It is decoration only and creates no connection. Both return a `Box` with the
bounds. `Box.at("rb")` uses the label anchors, and `Box.terms` holds the
centres of the summed glyphs for per-term labels:

```python
box = circuit.harmonic_sum("top", "bottom", (1, 2, 3), colors=shades)
for order, centre in zip((1, 2, 3), box.terms):
    circuit.label(f"E{order}", (centre[0], box.bottom + 2), anchor="ct")
circuit.box((10, 18), (60, 95), id="effective-junction")
```

The `examples/harmonic_junctions.py` example draws the symbol legend: the bare
X next to the boxed `m = 1, 2, 3` and `sin` symbols. It also shows an inductor
in series with a sinusoidal junction next to the multiharmonic junction it
acts like ([SVG preview](examples/harmonic_junctions.svg)).

## Architecture

The package separates the canvas from the symbols:

| Module | Contents |
| --- | --- |
| `cirquit.core` | `Circuit`: SVG root and unique ids, nodes, wire routing, labels, `box()`, `to_svg_document()`, and the drawing API symbols are built from |
| `cirquit.elements` | the symbol library: `capacitor`, `inductor`, `junction`, `harmonic_junction`, `harmonic_glyph`, `harmonic_sum`, `ground` |
| `cirquit.geometry` | value types and checks shared by both: `Point`, `Box`, `Branch`, `positive`, `offset`, … |
| `cirquit.node` | `Node`, a named, placed connection point |

A symbol is a plain function whose first argument is the circuit. It draws
only through the public drawing API: `circuit.branch(start, end)` resolves the
terminals into a `Branch`, `circuit.group(kind, id, branch=...)` opens a
semantic group with `data-from`/`data-to`, and `line`, `rect`, `dot` and
`path` add strokes in the circuit ink. Symbols are written in branch
coordinates (`branch.at(along, across)`), so one definition serves every
orientation. A new symbol is a new function in `cirquit.elements`, or in your
own script, and needs no change to the core:

```python
def resistor(circuit, start, end, *, id=None):
    branch = circuit.branch(start, end)
    group = circuit.group("resistor", id, branch=branch)
    lead, step = branch.length / 4, branch.length / 12
    points = [branch.at(lead + (i + 0.5) * step, 3 * (-1) ** i) for i in range(6)]
    circuit.path(
        group,
        [
            ("M", *branch.start.position),
            ("L", *branch.at(lead)),
            *(("L", *p) for p in points),
            ("L", *branch.at(3 * lead)),
            ("L", *branch.end.position),
        ],
    )


resistor(circuit, "top", "bottom", id="R")
```

The built-in symbols are also `Circuit` methods. `Circuit` binds each library
function as a class attribute (`capacitor = elements.capacitor`), and because
the function's first argument is the circuit, `circuit.capacitor(a, b)` is the
same call as `elements.capacitor(circuit, a, b)`. The method keeps the
function's signature and docstring, so there is no second definition to keep
in sync. There is no registry or plugin hook. Adding a method for a new symbol
is an optional one-line convenience, and the function works without it. The
core imports the library for these bindings, and the library never imports the
core at run time (`tests/test_elements.py` checks this boundary), so the
dependency points one way.

The core owns number formatting (`.12g`) and attribute order. Every symbol
therefore serializes coordinates the same way, and the output is
byte-identical from run to run.

**Why not svg.py.** [svg.py](https://github.com/orsinium-labs/svg) was
evaluated for building the symbols and is not used. It writes floats with
`repr` (`14.0`, `0.30000000000000004`, `1e-07`), while cirquit rounds to
twelve significant digits so that floating-point noise never reaches the
file. It also fixes its own attribute order, putting `stroke` before `x1`.
Adopting it would change every byte of existing figures, or would mean
passing preformatted strings, which defeats its typed fields. The canvas
needs lxml anyway to embed Vectex fragments and reorder connection dots.
Most importantly, a symbol's size comes from the circuit's ink, stroke
width, and line caps. svg.py has no notion of these, so element code would
get longer, not shorter. Its path commands are a trap here too: `svg.A` is
the `<a>` element, not an arc.

## Development

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
ruff format --check .
```
