"""Packaging invariants that are easy to break silently."""

from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path
from typing import Any

import pytest

import vecwire

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pyproject() -> dict[str, Any]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_version_matches_the_installed_distribution() -> None:
    assert vecwire.__version__ == importlib.metadata.version("vecwire")


def test_version_matches_pyproject(pyproject: dict[str, Any]) -> None:
    assert vecwire.__version__ == pyproject["project"]["version"]


def test_all_names_are_importable() -> None:
    for name in vecwire.__all__:
        assert hasattr(vecwire, name), name


def test_package_ships_type_information() -> None:
    assert (ROOT / "src" / "vecwire" / "py.typed").is_file()


def test_runtime_dependencies_stay_minimal(pyproject: dict[str, Any]) -> None:
    """VecTeX labels are optional; plain SVG labels must work without TeX."""
    names = {d.split(">")[0].split("=")[0].strip() for d in pyproject["project"]["dependencies"]}
    assert names == {"lxml"}
