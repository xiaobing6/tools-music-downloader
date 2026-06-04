# Force UTF-8 on Windows so rich / subprocess can print Chinese characters.
# music_downloader/console.py re-wraps sys.stdout with a UTF-8 writer
# before constructing rich.Console, which is the actual fix; this entry
# point just sets the env var so subprocess calls and child processes
# inherit the right encoding.
import os

os.environ.setdefault("PYTHONUTF8", "1")

from music_downloader.cli import main

if __name__ == "__main__":
    main()
