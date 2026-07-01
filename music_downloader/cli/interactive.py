"""Interactive CLI command parsing compatibility exports."""

from music_downloader.cli.workflow import (
    InteractiveCommand,
    build_interactive_options,
    parse_interactive_command,
)

__all__ = [
    "InteractiveCommand",
    "build_interactive_options",
    "parse_interactive_command",
]
