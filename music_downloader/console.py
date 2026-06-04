import importlib
import io
import sys
from types import ModuleType
from typing import Any, Optional

_rich_console_module: Optional[ModuleType]
try:
    _rich_console_module = importlib.import_module("rich.console")
    RICH_AVAILABLE = True
except ImportError:
    _rich_console_module = None
    RICH_AVAILABLE = False


def _force_utf8_stdout() -> None:
    """Reconfigure sys.stdout / sys.stderr to UTF-8 (errors=replace).

    On Windows the default codepage is cp1252. Rich 13/14's
    Console.__init__ reads `file.encoding` and uses it to pick a stream
    encoder, so we must reconfigure BEFORE constructing the Console.
    `reconfigure()` is a no-op on streams that already speak UTF-8.
    """
    from contextlib import suppress

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with suppress(Exception):
            reconfigure(encoding="utf-8", errors="replace")


class PlainConsole:
    def print(self, *objects: Any, style: Optional[str] = None, **kwargs: Any) -> None:
        print(*objects)

    def rule(self, title: str) -> None:
        print(title)


def make_console() -> Any:
    """Build a console appropriate for the current environment.

    - If rich is not importable, returns PlainConsole.
    - Otherwise returns a rich Console that writes to sys.stdout
      (after sys.stdout has been reconfigured to UTF-8). We do not
      pass `file=` so rich falls back to sys.stdout at write time,
      which is important for test capture via capsys.
    """
    if _rich_console_module is None:
        return PlainConsole()
    _force_utf8_stdout()
    return _rich_console_module.Console(stderr=False)  # type: ignore[call-arg]


console: Any = make_console()


# Re-export the wrapper class for any code that wants to wrap an
# arbitrary stream (kept here so the import graph stays small).
class _ForceUTF8Writer(io.TextIOBase):
    """Stream wrapper that advertises UTF-8 to consumers and re-encodes
    every write through UTF-8 to dodge non-ASCII-unfriendly codepages.

    Kept for backwards compatibility with test fixtures that may
    import it directly.
    """

    encoding = "utf-8"

    def __init__(self, inner: io.TextIOBase) -> None:
        self._inner = inner

    def writable(self) -> bool:
        return getattr(self._inner, "writable", lambda: True)()

    def isatty(self) -> bool:
        return getattr(self._inner, "isatty", lambda: False)()

    def flush(self) -> None:
        from contextlib import suppress

        with suppress(Exception):
            self._inner.flush()

    def write(self, data: str) -> int:  # type: ignore[override]
        if not isinstance(data, str):
            data = str(data)
        encoded = data.encode("utf-8", errors="replace").decode(
            getattr(self._inner, "encoding", "utf-8") or "utf-8", errors="replace"
        )
        return self._inner.write(encoded)
