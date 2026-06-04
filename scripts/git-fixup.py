#!/usr/bin/env python
"""git-fixup: repair loose remote-tracking refs after a failed git fetch.

On this machine `git fetch` deletes refs/remotes/origin/* but fails to
write new loose-ref files (git 2.53.0 on Windows).  This script:
  1. Runs `git fetch` (or skips it if --no-fetch)
  2. Reads the actual remote SHAs via `git ls-remote`
  3. Writes loose ref files under .git/refs/remotes/origin/
  4. Prints a before/after summary

Usage:
    python git-fixup.py              # fetch + fix
    python git-fixup.py --no-fetch   # only fix, useful after manual fetch
    python git-fixup.py --dry-run    # show what would be done
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], check: bool = True) -> str:
    """Run a shell command and return stripped stdout."""
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"FAILED: {' '.join(cmd)}", file=sys.stderr)
        print(r.stderr, file=sys.stderr)
        sys.exit(1)
    return r.stdout.strip()


def ls_remote(origin_url: str) -> dict[str, str]:
    """Parse `git ls-remote <origin>` into {ref_name: sha}."""
    out = run(["git", "ls-remote", origin_url])
    mapping: dict[str, str] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            sha, ref = parts
            mapping[ref] = sha
    return mapping


def get_fetch_refspec(cfg_path: Path) -> str:
    """Read remote.origin.fetch from git config."""
    val = run(["git", "config", "--get", "remote.origin.fetch"])
    return val  # e.g. "+refs/heads/*:refs/remotes/origin/*"


def remote_name() -> str:
    return run(["git", "config", "--get", "branch.*.remote"], check=False).strip() or "origin"


def main() -> None:
    ap = argparse.ArgumentParser(description="Repair remote-tracking refs after broken git fetch")
    ap.add_argument("--no-fetch", action="store_true", help="Skip git fetch, only write refs")
    ap.add_argument("--dry-run", action="store_true", help="Show plan without writing")
    ap.add_argument("-q", "--quiet", action="store_true", help="Silent on success")
    args = ap.parse_args()

    git_dir = Path(run(["git", "rev-parse", "--git-dir"]))
    origin = run(["git", "config", "--get", "remote.origin.url"])
    refs_dir = git_dir / "refs" / "remotes" / "origin"
    refs_dir.mkdir(parents=True, exist_ok=True)

    # Current state (may be empty if refs dir was nuked)
    current = {}
    if refs_dir.exists():
        for p in refs_dir.iterdir():
            if p.is_file():
                current[p.name] = p.read_text().strip()

    # Fetch from remote
    if not args.no_fetch:
        if not args.quiet:
            print(f"Fetching from {origin} ...")
        run(["git", "fetch", "origin"])
        if not args.quiet:
            print("fetch done (refs may still be stale on this machine)")

    # On this machine `git fetch` sometimes removes the entire origin/ directory.
    # Recreate it after fetch so we can write loose ref files.
    refs_dir.mkdir(parents=True, exist_ok=True)

    # Desired state from ls-remote
    desired = ls_remote(origin)

    # Filter to heads only (refs/heads/* -> origin/<branch>)
    desired_heads = {
        ref.removeprefix("refs/heads/"): sha
        for ref, sha in desired.items()
        if ref.startswith("refs/heads/")
    }

    changes = []
    for branch, sha in sorted(desired_heads.items()):
        old = current.get(branch)
        if old != sha:
            changes.append((branch, old or "(missing)", sha))

    if not changes:
        if not args.quiet:
            print("All refs already up to date.")
        return

    # Summary
    print(f"\n{'branch':20s} {'old':10s} -> {'new':10s}")
    print("-" * 44)
    for branch, old, new in changes:
        print(f"{branch:20s} {old[:8]:10s} -> {new[:8]:10s}")

    if args.dry_run:
        print("\nDry run — no files written.")
        return

    # Write loose refs
    for branch, _, sha in changes:
        p = refs_dir / branch
        p.write_text(sha + "\n")
        if not args.quiet:
            print(f"Wrote {p}")

    if not args.quiet:
        print(f"\n{len(changes)} ref(s) repaired. Run `git status` to verify.")


if __name__ == "__main__":
    main()
