"""Utility helpers for accessing packaged resources.

When running the application from source the resources live next to this
module.  In the bundled executable (PyInstaller's ``onefile`` mode) the files
are extracted to a temporary directory whose location is exposed via the
``_MEIPASS`` attribute.  Using :mod:`pathlib` to resolve the absolute directory
ensures a single code path that works for both scenarios.
"""

from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Match


@lru_cache(maxsize=1)
def _resource_root() -> Path:
    """Return the absolute path to the resources directory."""

    if hasattr(sys, "_MEIPASS"):
        base = Path(getattr(sys, "_MEIPASS"))
        for candidate in (
            base / "app" / "resources",
            base / "resources",
            base,
        ):
            if (candidate / "styles.qss").exists() or (candidate / "icons").exists():
                return candidate

    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    """Join ``parts`` onto the resource directory and return a path.

    The helper makes it trivial to reference assets regardless of whether the
    project is executed from source or from a frozen bundle.  A :class:`Path`
    object is returned so callers can convert it to :class:`str` when needed.
    """

    return _resource_root().joinpath(*parts)


def _resolve_stylesheet_urls(stylesheet: str) -> str:
    """Expand relative ``url(...)`` declarations to absolute paths.

    Qt resolves icon URLs relative to the current working directory when a
    stylesheet is applied from a string, which breaks when the application is
    packaged.  Rewriting them to absolute paths keeps the rich interface intact
    for both development and packaged environments.
    """

    def _replace(match: Match[str]) -> str:
        quote, relative = match.group(1) or '"', match.group(2)
        absolute = resource_path(*relative.split("/")).as_posix()
        return f"url({quote}{absolute}{quote})"

    pattern = re.compile(r"url\((['\"]?)(icons/[^)]+)\1\)")
    return pattern.sub(_replace, stylesheet)


def load_stylesheet(name: str = "styles.qss") -> str:
    """Return the stylesheet contents with resolved icon paths."""

    stylesheet = resource_path(name).read_text(encoding="utf-8")
    return _resolve_stylesheet_urls(stylesheet)


def list_available_icons() -> Iterable[Path]:
    """Yield paths to the available SVG icons.

    This is mainly useful for debugging to ensure the assets are bundled
    correctly when building the standalone executable.
    """

    return resource_path("icons").glob("*.svg")


__all__ = ["load_stylesheet", "resource_path", "list_available_icons"]
