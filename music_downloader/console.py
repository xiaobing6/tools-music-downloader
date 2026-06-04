import importlib
from types import ModuleType
from typing import Any, Optional

_rich_console_module: Optional[ModuleType]
try:
    _rich_console_module = importlib.import_module("rich.console")
    RICH_AVAILABLE = True
except ImportError:
    _rich_console_module = None
    RICH_AVAILABLE = False


class PlainConsole:
    def print(self, *objects: Any, style: Optional[str] = None, **kwargs: Any) -> None:
        print(*objects)

    def rule(self, title: str) -> None:
        print(title)


if _rich_console_module is None:
    console: Any = PlainConsole()
else:
    # Force UTF-8 encoding so Chinese characters (and all Unicode) print
    # correctly on Windows CI runners where the default codepage is cp1252.
    console = _rich_console_module.Console(
        encoding="utf-8",
        # Disable auto-detection of colour system; let Rich pick the best
        # one based on the actual terminal capabilities.
        force_terminal=None,
    )
