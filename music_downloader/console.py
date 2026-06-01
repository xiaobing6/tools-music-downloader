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
    console = _rich_console_module.Console()
