"""Minimal backend entrypoint for Phase 1 foundation setup.

This module currently only confirms that the Python layer is reachable. Audio
conversion logic will be implemented in later phases.
"""

from __future__ import annotations


def main() -> None:
    """Print a simple readiness message."""
    print("Backend ready: awaiting conversion commands.")


if __name__ == "__main__":
    main()
