"""GdStudio upstream API client and compatibility functions."""

from __future__ import annotations

import json
import math
from typing import Any

from music_downloader.config import (
    API_RETRY_ATTEMPTS,
    CF_RETRY_ATTEMPTS,
    MAX_PER_PAGE,
    PAGE_NAV_TIMEOUT_MS,
    SEARCH_TYPE_MAP,
)
from music_downloader.console import console
from music_downloader.domain.enums import Bitrate, Source
from music_downloader.domain.models import SearchOptions, Song
from music_downloader.infrastructure.encoding import url_encode


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


class GdStudioClient:
    def __init__(self, page: Any):
        self.page = page

    def search(self, options: SearchOptions) -> list[dict[str, Any]]:
        return search_with_pagination(
            self.page,
            options.keyword,
            options.source.value,
            options.search_type.value,
            options.number,
        )

    def get_play_url(self, song: Song, source: Source | str, bitrate: Bitrate | str) -> str:
        return get_play_url(
            self.page, song.to_legacy_dict(), _enum_value(source), _enum_value(bitrate)
        )

    def get_lyric(self, song: Song, source: Source | str) -> str:
        return get_lyric(self.page, song.to_legacy_dict(), _enum_value(source))

    def get_pic_url(self, song: Song, source: Source | str) -> str:
        return get_pic_url(self.page, song.to_legacy_dict(), _enum_value(source))


def compute_signature(page: Any, search_id: str) -> str:
    """复用站点前端的 crc32 函数计算签名。

    站点把签名算法封装在页面 JS 中，自行实现容易因混淆/变更而失效，
    因此直接通过 page.evaluate 调用前端 `crc32(urlEncode(...))` 的等价逻辑。
    调用方应传入已经过 `url_encode` 编码后的标识字符串。
    """
    return page.evaluate(
        """(searchId) => {
            return crc32(searchId);
        }""",
        search_id,
    )


def wait_for_cloudflare(page: Any, max_retries: int = CF_RETRY_ATTEMPTS) -> bool:
    for attempt in range(1, max_retries + 1):
        cf_cookie: str | None = None
        for cookie in page.context.cookies():
            if cookie.get("name") == "cf_clearance":
                cf_cookie = cookie.get("value")
                break
        if cf_cookie:
            console.print(f"  ✓ Cloudflare 验证通过 (第 {attempt} 次尝试)", style="green")
            return True
        if attempt < max_retries:
            console.print(
                f"  ⚠ 未检测到 cf_clearance，第 {attempt + 1} 次重试...",
                style="yellow",
            )
            page.reload(wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
    return False


def refresh_cloudflare(page: Any) -> bool:
    console.print("  ⚠ Cloudflare 验证可能已过期，尝试重新验证...", style="yellow")
    page.reload(wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
    return wait_for_cloudflare(page)


def fetch_api(page: Any, body: str) -> tuple[int, str]:
    """通过页面上下文向 /api.php 发送 POST 请求，返回 (状态码, 响应文本)。"""
    result = page.evaluate(
        """async (body) => {
            const resp = await fetch('/api.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json, text/javascript, */*; q=0.01'
                },
                body: body
            });
            return { status: resp.status, text: await resp.text() };
        }""",
        body,
    )
    return result["status"], result["text"]


def _load_json_response(result_text: str, error_message: str) -> Any:
    """解析 JSON 响应文本，失败时打印错误并返回 None。"""
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        console.print(f"  ✗ {error_message}，原始内容: {result_text[:500]}", style="red")
        return None


def fetch_with_cf_retry(
    page: Any,
    body: str,
    resource_name: str,
    *,
    attempts: int = API_RETRY_ATTEMPTS,
) -> tuple[int, str]:
    """对 /api.php 一次 fetch 加上 Cloudflare 自动重试。

    行为：
    - 遇到 403 时调用 refresh_cloudflare 刷新一次，然后重试。
    - CF 刷新失败立即返回 (403, "")，调用方应放弃。
    - 用尽 attempts 后返回最后一次 (status, text)。
    - 401/502 等非 403 状态码不会被当作"需要刷 CF"，按原样返回。
    """
    last_status = 0
    last_text = ""
    for _ in range(attempts):
        status, result_text = fetch_api(page, body)
        last_status, last_text = status, result_text
        if status != 403:
            return status, result_text
        console.print(
            f"  ✗ 获取{resource_name}失败 (HTTP 403) - Cloudflare 验证可能已过期",
            style="yellow",
        )
        if not refresh_cloudflare(page):
            return 403, ""
    return last_status, last_text


def search_with_pagination(
    page: Any,
    keyword: str,
    source: str,
    search_type: str,
    total: int,
) -> list[dict[str, Any]]:
    all_results: list[dict[str, Any]] = []
    remaining = total
    current_page = 1
    total_pages = int(math.ceil(float(total) / MAX_PER_PAGE))
    encoded_name = url_encode(keyword)
    api_type = SEARCH_TYPE_MAP.get(search_type, "search")

    while remaining > 0:
        # 始终用 MAX_PER_PAGE 作为单页请求量。
        # 如果最后一页用 min(remaining, MAX_PER_PAGE) 会把 count 缩小，
        # 服务端按 offset = (pages - 1) * count 计算偏移时就会错位，
        # 返回前面页的数据，造成重复（被去重后总数变少）。
        count = MAX_PER_PAGE
        if total_pages > 1:
            console.print(
                f"      第 {current_page}/{total_pages} 页: 请求 {count} 条...",
                style="dim",
            )

        signature = compute_signature(page, encoded_name)
        body = (
            f"types={api_type}&count={count}&source={source}"
            f"&pages={current_page}&name={encoded_name}&s={signature}"
        )
        status, result_text = fetch_with_cf_retry(page, body, "搜索结果")

        if status != 200:
            if status == 401:
                console.print(
                    "  ✗ 请求被拒绝 (HTTP 401) - 签名验证失败，站点版本或签名算法可能已更新",
                    style="red",
                )
            elif status == 502:
                console.print(
                    "  ✗ 服务器连接中断 (HTTP 502) - 请稍后重试",
                    style="red",
                )
            else:
                console.print(f"  ✗ 请求失败 (HTTP {status})", style="red")
            if result_text:
                console.print(f"  响应内容: {result_text[:200]}", style="dim")
            break

        data = _load_json_response(result_text, "响应解析失败")
        if not isinstance(data, list) or not data:
            break

        all_results.extend(data)
        remaining -= len(data)
        current_page += 1

        if len(data) < count:
            break

    return all_results[:total]


def _signed_url_get(page: Any, body: str, resource_name: str) -> str:
    """带 Cloudflare 重试的 URL 资源拉取，仅返回 url 字符串。"""
    status, result_text = fetch_with_cf_retry(page, body, resource_name)
    if status != 200:
        if status != 403:
            console.print(
                f"  ✗ 获取{resource_name}失败 (HTTP {status})",
                style="red",
            )
        return ""
    data = _load_json_response(result_text, f"解析{resource_name}响应失败")
    if not isinstance(data, dict):
        return ""
    return data.get("url", "")


def get_play_url(page: Any, song: dict[str, Any], source: str, bitrate: str = "320") -> str:
    url_id = str(song.get("url_id", song.get("id", "")))
    if not url_id:
        return ""
    encoded_id = url_encode(url_id)
    signature = compute_signature(page, encoded_id)
    body = f"types=url&id={encoded_id}&source={source}&br={bitrate}&s={signature}"
    return _signed_url_get(page, body, "播放链接")


def get_lyric(page: Any, song: dict[str, Any], source: str) -> str:
    lyric_id = str(song.get("lyric_id", ""))
    if not lyric_id:
        return ""
    encoded_id = url_encode(lyric_id)
    signature = compute_signature(page, encoded_id)
    body = f"types=lyric&id={encoded_id}&source={source}&s={signature}"
    status, result_text = fetch_with_cf_retry(page, body, "歌词")
    if status != 200:
        return ""
    data = _load_json_response(result_text, "解析歌词响应失败")
    if isinstance(data, dict):
        return data.get("lyric", "")
    return ""


def get_pic_url(page: Any, song: dict[str, Any], source: str) -> str:
    pic_id = str(song.get("pic_id", ""))
    if not pic_id:
        return ""
    encoded_id = url_encode(pic_id)
    signature = compute_signature(page, encoded_id)
    body = f"types=pic&id={encoded_id}&source={source}&s={signature}"
    return _signed_url_get(page, body, "封面图")
