"""Shared source and compiled runtime path resolution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ACTIVE_PROFILE_MARKER = ".active-profile"
RECOVERY_PROFILE_NAME = "recovery"


def runtime_root(
    module_file: str | os.PathLike[str],
    *,
    compiled: bool | None = None,
    executable: str | os.PathLike[str] | None = None,
) -> Path:
    """Return the stable application root for source and Nuitka runs."""
    if compiled is None:
        compiled = "__compiled__" in globals()
    if compiled:
        executable_path = Path(executable if executable is not None else sys.argv[0])
        return executable_path.resolve().parent
    return Path(module_file).resolve().parents[2]


def active_chrome_profile(profile_root: str | os.PathLike[str]) -> Path:
    """Resolve the profile activated after a non-destructive recovery."""
    root = Path(profile_root)
    try:
        active_name = (root / ACTIVE_PROFILE_MARKER).read_text(encoding="utf-8").strip()
    except OSError:
        return root
    if active_name == RECOVERY_PROFILE_NAME:
        return root / RECOVERY_PROFILE_NAME
    return root
