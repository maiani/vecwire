# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Use ty for type checking in development and CI instead of mypy.

## [0.2.0] - 2026-10-05

### Changed

- **Renamed from cirquit to VecWire.** The distribution and import name is now
  `vecwire` (was `cirquit`), because `cirquit` on PyPI belongs to an unrelated
  quantum-computing platform; the new name joins the `vec` family of its
  siblings. Output is unchanged.

## [0.1.0] - 2026-10-05

### Added

- `Circuit`, an SVG canvas of named, positioned nodes joined by wires, with
  `row()`, `column()` and `nodes()` to declare them, `via` routing, a
  per-circuit or per-wire `corner_radius`, labels from plain text or a VecTeX
  fragment, dashed `box()` enclosures, and `to_svg_document()`, the only
  interface FigWorks needs to place a circuit.
- The symbol library: `capacitor`, `inductor`, `ground`, the bare-X
  `junction`, the boxed `harmonic_junction` for one `cos(mφ)` or `sin(mφ)`
  term, and `harmonic_sum` for a multiharmonic junction.
- Byte-identical output: the core owns number formatting (`.12g`) and
  attribute order.
- Examples reproducing a circuit-QED sketch (`fig1a_cqed.py`) and the junction
  symbol legend (`harmonic_junctions.py`).
- Type information: the package ships `py.typed` and passes `mypy --strict`.
  Label fragments are typed by the structural `vecwire.core.Fragment`
  protocol (`width`, `height`, `to_svg()`), so VecTeX stays optional.
- `vecwire.__version__`, kept equal to the distribution version by a test.
- Package metadata: MIT licence (with a `LICENSE` file), keywords,
  classifiers, and project URLs.

### Changed

- The bare-X `junction` draws its leads on to the centre of the X, so the wire
  runs continuously through the symbol instead of stopping at the square's
  edge.
- Python 3.12 is the minimum supported version, matching VecTeX and VecView.
- The build backend is hatchling, as in the sibling projects; the wheel ships
  `py.typed`.
- Ruff checks the `B`, `E`, `F`, `I`, `N`, `RUF`, `S` and `UP` rule sets, and
  pytest runs with `--strict-config --strict-markers`.
