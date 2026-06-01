import hashlib
import json
import math

from .config import HOSTNAME, MAX_PER_PAGE, SEARCH_TYPE_MAP
from .utils import url_encode


def compute_signature(hostname, version, timestamp, search_id):
    padded_version = "".join(part.zfill(2) for part in version.split("."))
    ts_first9 = str(timestamp)[:9]
    signing_string = f"{hostname}|{padded_version}|{ts_first9}|{search_id}"
    return hashlib.md5(signing_string.encode()).hexdigest()[-8:].upper()


def wait_for_cloudflare(page, max_retries=3):
    for attempt in range(1, max_retries + 1):
        cf_cookie = None
        for cookie in page.context.cookies():
            if cookie.get("name") == "cf_clearance":
                cf_cookie = cookie.get("value")
                break
        if cf_cookie:
            print(f"  ✓ Cloudflare 验证通过 (第 {attempt} 次尝试)")
            return True
        if attempt < max_retries:
            print(f"  ⚠ 未检测到 cf_clearance，第 {attempt + 1} 次重试...")
            page.reload(wait_until="networkidle", timeout=60000)
    return False


def refresh_cloudflare(page):
    print("  ⚠ Cloudflare 验证可能已过期，尝试重新验证...")
    page.reload(wait_until="networkidle", timeout=60000)
    return wait_for_cloudflare(page)


def fetch_api(page, body):
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


def get_timestamp(page):
    return page.evaluate(
        """async () => {
            const resp = await fetch('/time');
            return await resp.text();
        }"""
    )


def _load_json_response(result_text, error_message):
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        print(f"  ✗ {error_message}，原始内容: {result_text[:500]}")
        return None


def search_with_pagination(page, keyword, source, search_type, total, version):
    all_results = []
    remaining = total
    current_page = 1
    total_pages = int(math.ceil(float(total) / MAX_PER_PAGE))
    encoded_name = url_encode(keyword)
    api_type = SEARCH_TYPE_MAP.get(search_type, "search")
    cf_retry_count = 0

    while remaining > 0:
        count = min(remaining, MAX_PER_PAGE)
        page_label = f"第 {current_page}/{total_pages} 页"
        if total_pages > 1:
            print(f"      {page_label}: 请求 {count} 条...")

        timestamp = get_timestamp(page)
        signature = compute_signature(HOSTNAME, version, timestamp, encoded_name)
        body = (
            f"types={api_type}&count={count}&source={source}&pages={current_page}&name={encoded_name}&s={signature}"
        )
        status, result_text = fetch_api(page, body)

        if status != 200:
            if status == 401:
                print(
                    "  ✗ 请求被拒绝 (HTTP 401) - 签名验证失败，"
                    "站点版本或签名算法可能已更新"
                )
            elif status == 403:
                print("  ✗ 请求被拒绝 (HTTP 403) - Cloudflare 验证可能已过期")
                cf_retry_count += 1
                if cf_retry_count <= 2 and refresh_cloudflare(page):
                    continue
            elif status == 502:
                print("  ✗ 服务器连接中断 (HTTP 502) - 请稍后重试")
            else:
                print(f"  ✗ 请求失败 (HTTP {status})")
            print(f"  响应内容: {result_text[:200]}")
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


def _fetch_resource_url(page, body, resource_name):
    status, result_text = fetch_api(page, body)
    if status == 403:
        return status, ""
    if status != 200:
        print(f"  ✗ 获取{resource_name}失败 (HTTP {status})")
        return status, ""

    data = _load_json_response(result_text, f"解析{resource_name}响应失败")
    if not isinstance(data, dict):
        return status, ""
    return status, data.get("url", "")


def get_play_url(page, song, source, version, bitrate="320"):
    url_id = str(song.get("url_id", song.get("id", "")))
    if not url_id:
        return ""
    for _attempt in range(1, 3):
        timestamp = get_timestamp(page)
        encoded_id = url_encode(url_id)
        signature = compute_signature(HOSTNAME, version, timestamp, encoded_id)
        body = f"types=url&id={encoded_id}&source={source}&br={bitrate}&s={signature}"
        status, url = _fetch_resource_url(page, body, "播放链接")
        if status == 403:
            print("  ✗ 获取播放链接失败 (HTTP 403) - Cloudflare 验证可能已过期")
            if refresh_cloudflare(page):
                continue
            return ""
        return url
    return ""


def get_lyric(page, song, source, version):
    lyric_id = str(song.get("lyric_id", ""))
    if not lyric_id:
        return ""
    for _attempt in range(1, 3):
        timestamp = get_timestamp(page)
        encoded_id = url_encode(lyric_id)
        signature = compute_signature(HOSTNAME, version, timestamp, encoded_id)
        body = f"types=lyric&id={encoded_id}&source={source}&s={signature}"
        status, result_text = fetch_api(page, body)
        if status == 403:
            if refresh_cloudflare(page):
                continue
            return ""
        if status != 200:
            return ""
        data = _load_json_response(result_text, "解析歌词响应失败")
        if isinstance(data, dict):
            return data.get("lyric", "")
        return ""
    return ""


def get_pic_url(page, song, source, version):
    pic_id = str(song.get("pic_id", ""))
    if not pic_id:
        return ""
    for _attempt in range(1, 3):
        timestamp = get_timestamp(page)
        encoded_id = url_encode(pic_id)
        signature = compute_signature(HOSTNAME, version, timestamp, encoded_id)
        body = f"types=pic&id={encoded_id}&source={source}&s={signature}"
        status, url = _fetch_resource_url(page, body, "封面图")
        if status == 403:
            if refresh_cloudflare(page):
                continue
            return ""
        return url
    return ""
