# AGENTS.md

## Project Overview

This is a CLI tool for searching and downloading music from `music.gdstudio.org`. It uses Playwright to handle Cloudflare protection and the site's API to search, stream, and download MP3 files with full metadata (ID3 tags, cover art, lyrics).

## Tech Stack

- **Language**: Python 3
- **Dependencies**: `playwright` (headless browser for Cloudflare bypass and API calls), `mutagen` (MP3 ID3 tag read/write)
- **No test framework** is currently set up.

## Project Structure

```
download.py          # Main script — all logic lives here (search, download, ID3 tagging, CLI)
requirements.txt     # Python dependencies
downloads/           # Output directory for downloaded MP3 files (gitignored)
```

## How to Run

```bash
pip install -r requirements.txt
playwright install chromium
python download.py -k "关键词"              # Search and download (default: 网易云, 320kbps, 20 results)
python download.py -k "Beyond" --search-only # Search only, no download
python download.py -k "Beyond" --select      # Search then pick songs to download
python download.py -i                        # Interactive mode
```

## Key Architecture

### API Interaction Flow

1. Launch Playwright browser → visit `music.gdstudio.org` → pass Cloudflare verification
2. Extract `mkPlayer.version` from the page (used for signature computation)
3. All API calls go to `/api.php` via POST with a computed MD5 signature (`compute_signature`)
4. Signature formula: `MD5(hostname | zero-padded-version | timestamp[:9] | search_id)[-8:].upper()`

### Core Functions in `download.py`

| Function | Purpose |
|---|---|
| `compute_signature()` | Generate API request signature |
| `search_with_pagination()` | Search songs with auto-pagination (max 99 per page) |
| `get_play_url()` | Get MP3 playback URL for a song |
| `get_lyric()` | Fetch lyrics for a song |
| `get_pic_url()` | Fetch cover art URL for a song |
| `download_song()` | Download MP3 + embed ID3 tags (cover, lyrics, metadata) |
| `embed_id3_tags()` | Write ID3v2 tags (TIT2, TPE1, TALB, TRCK, APIC, USLT) |
| `interactive_mode()` | REPL-style interactive search/download loop |

### Supported Music Sources

`netease`, `migu`, `kuwo`, `ytmusic`, `tidal`, `qobuz`, `deezer`, `spotify`, `tencent`, `ximalaya`, `joox`, `apple`

### CLI Arguments

| Flag | Description |
|---|---|
| `-k / --keyword` | Search keyword (default: "Beyond") |
| `-s / --source` | Music source (default: "netease") |
| `-n / --number` | Number of results (default: 20) |
| `-t / --type` | Search type: song/album/playlist |
| `-o / --output` | Output directory |
| `-f / --format` | Output format: table/json/list |
| `-b / --bitrate` | Bitrate: 128/192/320/flac |
| `--search-only` | Search without downloading |
| `--select` | Choose songs interactively after search |
| `--no-lyric` | Skip lyrics embedding |
| `--no-cover` | Skip cover art embedding |
| `-i / --interactive` | Interactive REPL mode |

## Coding Conventions

- Single-file architecture — all logic is in `download.py`
- Chinese-language CLI output and comments
- No external config files; all constants defined at module top
- Error handling: retry with Cloudflare refresh on HTTP 403; retry download up to 2 times
- Filename sanitization replaces `\/:*?"<>|` with `_`
- Downloaded files are named `[song_id] artist - name.mp3`

## Common Modification Scenarios

- **Adding a new music source**: Add the source name to `VALID_SOURCES` list; the API handles routing server-side
- **Changing default settings**: Modify `DEFAULT_KEYWORD`, `DEFAULT_SOURCE`, `DEFAULT_NUMBER` constants
- **Adjusting ID3 tag writing**: Edit `embed_id3_tags()` — currently writes TIT2, TPE1, TALB, TRCK, APIC, USLT
- **Changing download behavior**: Modify `download_song()` — retry logic, proxy URL pattern, temp file handling
- **API signature changes**: Update `compute_signature()` if the site changes its signing algorithm
