# Force UTF-8 encoding on Windows so rich / subprocess can print Chinese
# characters.  Must run before any other import / Console instantiation.
import os
import sys

os.environ.setdefault("PYTHONUTF8", "1")

# Nuitka onefile bundle may not honour PYTHONUTF8 at runtime; reconfigure
# directly so sys.stdout / sys.stderr always use UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from music_downloader.cli import main

if __name__ == "__main__":
    main()
