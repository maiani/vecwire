# Development

Setup and validation are in the README's
[Development](../README.md#development) section; the contributor rules are in
[AGENTS.md](../AGENTS.md).

## Releases

`.github/workflows/publish.yml` publishes tags named `v<version>`. It checks
that the tag matches `pyproject.toml`, runs the CI matrix against that tag,
builds both distributions (the wheel from the sdist), and runs
`twine check --strict` before publishing the same artifacts. Python 3.15 is
experimental; its job may fail while the supported 3.12–3.14 jobs must pass.

Publishing goes through a
[Trusted Publisher on PyPI](https://docs.pypi.org/trusted-publishers/), configured
with these exact values:

| Field | Value |
| --- | --- |
| Project name | `vecwire` |
| GitHub owner | `maiani` |
| Repository | `vecwire` |
| Workflow filename | `publish.yml` |
| Environment | `pypi` |

The GitHub repository needs the matching `pypi` environment. Publishing uses
GitHub OIDC, with `id-token: write` granted only to the publish job; no PyPI API
token is needed. Before the first release the project does not exist on PyPI,
so the publisher is added as a
[pending publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/),
which creates the project on the first upload.

For a release:

1. Update the version in `pyproject.toml` and `src/vecwire/__init__.py` together.
2. Move the relevant `Unreleased` changelog entries into a dated release section.
   The README is the PyPI page, so its image and links are absolute: point them
   at the new tag.
3. Run validation and build the wheel and sdist. Commit the release changes.
4. Push `main`, wait for CI to pass, then push only the new tag, such as
   `v0.3.0`. Its push triggers publishing. Never push all tags at once: any
   pushed `v*` tag publishes.

The workflow can also be dispatched manually with an existing tag to retry
an upload. It always checks out `refs/tags/<tag>`, including for CI and builds.
Versions already uploaded to PyPI cannot be overwritten; fix release content
under a new version.
