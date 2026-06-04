import sys
from contextlib import suppress
from typing import Any, Optional

RichTable: Any
try:
    from rich.table import Table as RichTable
except ImportError:
    RichTable = None


def _force_utf8_stdout() -> None:
    """Reconfigure sys.stdout / sys.stderr to UTF-8 (errors=replace).

    On Windows the default codepage is cp1252. Rich 13/14's
    Console.__init__ reads `file.encoding` and uses it to pick a stream
    encoder, so we must reconfigure BEFORE constructing the Console.
    `reconfigure()` is a no-op on streams that already speak UTF-8.
    """
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
    try:
        from rich.console import Console as RichConsole
    except ImportError:
        return PlainConsole()
    _force_utf8_stdout()
    return RichConsole(stderr=False)  # type: ignore[call-arg,arg-type]


console: Any = make_console()
