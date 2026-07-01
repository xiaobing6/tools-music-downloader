"""Selection parsing for CLI interactive and --select flows."""

from __future__ import annotations

from collections.abc import Callable


def parse_selection(
    selection: str,
    total: int,
    *,
    warn: Callable[[str], None] | None = None,
) -> list[int]:
    """Parse 1,3,5-7 style input into zero-based indices."""
    indices: set[int] = set()
    for part in selection.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start_num = int(start)
                end_num = int(end)
            except ValueError:
                continue
            if start_num > end_num:
                if warn is not None:
                    warn(f"  ⚠ 已反转区间 {start_num}-{end_num} 为 {end_num}-{start_num}")
                start_num, end_num = end_num, start_num
            for index in range(start_num, min(end_num, total) + 1):
                if 1 <= index <= total:
                    indices.add(index - 1)
            continue

        try:
            index = int(part)
        except ValueError:
            continue
        if 1 <= index <= total:
            indices.add(index - 1)
    return sorted(indices)
