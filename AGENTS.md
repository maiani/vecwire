# VecWire agent guidance

VecWire is a focused Python package for readable, deterministic SVG circuit
schematics, especially circuit-QED publication figures. Keep its public API
small and grounded in the Fig. 1(a) example.

- Connect components through named, positioned `Node` objects. A node is a placed
  point; a net may contain several nodes joined by wires. Via points affect only
  routing and do not establish connectivity.
- Accept node names as concise references in examples. A wire may pass through
  several connected nodes, and its centerline must pass through each of them.
- Preserve semantic SVG IDs and `data-from`/`data-to` endpoint metadata.
- Render each routed wire as one SVG path so line joins and corner radii work.
- Keep output deterministic and editable; use `to_svg_document()` for FigWorks integration.
- Treat VecTeX as optional. Plain SVG labels must work without TeX.
- Add symbols or routing features when a real figure needs them; avoid a circuit
  simulation or netlist abstraction without an explicit requirement.
- Keep symbols in `vecwire.elements` as plain functions of the circuit, drawn
  only through the public drawing API of `vecwire.core` (`branch`, `group`,
  `line`, `rect`, `dot`, `path`) and `vecwire.geometry`. The library must not
  import the core at run time; built-in symbols are bound as `Circuit` methods
  by one class attribute each. No registries or plugin hooks.
- Leave number formatting to the core so output stays byte-identical; check
  `examples/fig1a.svg` is unchanged after refactors.
- Preserve user-authored examples and unrelated changes.

## Development

- Supported Python: 3.12 and newer.
- `uv venv && uv pip install -e '.[dev]'` for a development environment; add
  `.[tex]` (and a TeX installation) to exercise VecTeX labels.
- Run `ruff format --check .`, `ruff check .`, `ty check`, and `pytest` before
  reporting a change complete. ty checks `src`; type the
  duck-typed inputs with a `Protocol`, not `Any`.
- Run `python examples/fig1a_cqed.py` and `python examples/harmonic_junctions.py`
  after touching drawing code, and diff what they write against
  `examples/fig1a.svg` and `examples/harmonic_junctions.svg`. Any byte that
  changes must be one the change intended.
- Keep `CHANGELOG.md` current in Keep a Changelog 1.1.0 format.
- Do not commit, tag, upload, or publish unless the user explicitly asks.
