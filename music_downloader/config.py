"""全局常量、默认值和支持的平台列表。"""

BASE_URL = "https://music.gdstudio.org"
HOSTNAME = "music.gdstudio.org"
PROXY_BASE_URL = "https://music-proxy.gdstudio.org"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
)

DEFAULT_KEYWORD = "Beyond"
DEFAULT_SOURCE = "netease"
DEFAULT_NUMBER = 20
DEFAULT_BITRATE = "320"
FALLBACK_VERSION = "2026.5.10"
MAX_PER_PAGE = 99
MIN_DOWNLOAD_BYTES = 10240
DOWNLOAD_RETRIES = 3
DOWNLOAD_RETRY_BACKOFF_SEC = 3.0
API_RETRY_ATTEMPTS = 3
CF_RETRY_ATTEMPTS = 3
INTER_SONG_DELAY_SEC = 1.0
REQUEST_TIMEOUT_MS = 300000
COVER_TIMEOUT_MS = 30000
PAGE_NAV_TIMEOUT_MS = 60000

VALID_SOURCES = [
    "netease",
    "migu",
    "kuwo",
    "ytmusic",
    "tidal",
    "qobuz",
    "deezer",
    "spotify",
    "tencent",
    "ximalaya",
    "joox",
    "apple",
]

VALID_FORMATS = ["table", "json", "list"]
VALID_BITRATES = ["128", "192", "320", "flac"]

SEARCH_TYPE_MAP = {
    "song": "search",
    "album": "search_album",
    "playlist": "search_playlist",
}
