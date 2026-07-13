from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_gui_docs_match_workbench_contract() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "1280x800" in readme
    assert "1024x720" in readme
    assert "搜索" in readme and "更多设置" in readme
    assert "1180px" in agents
    assert "日志默认折叠" in agents
    assert "1266x1013" not in readme
    assert "音源、搜索类型和结果数量是常用设置" in readme
    assert "音质" in readme and "更多设置" in readme
    assert "音源、类型、结果数量为常用设置" in agents
    assert "10px" in agents


def test_gui_docs_cover_visual_polish_contract() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "使用 `scrollbar-gutter: stable` 预留" not in readme
    assert "固定外壳" in readme
    assert "内部滚动" in readme
    assert "下拉箭头" in readme
    assert "使用 `scrollbar-gutter: stable` 预留" not in agents
    assert "固定外壳" in agents
    assert "内部滚动" in agents
    assert "下拉箭头" in agents
    assert "紧凑音乐库" in readme
    assert "60px" in readme
    assert "紧凑音乐库" in agents
    assert "60px" in agents
    assert "内容加权" in readme
    assert "按钮文字保持稳定" in readme
    assert "内容加权" in agents
    assert "按钮文字保持稳定" in agents
    assert "Windows 应用图标" in readme
    assert "music_downloader.ico" in readme
    assert "Windows 应用图标" in agents
    assert "music_downloader.ico" in agents
    assert "全局关闭确认" in readme
    assert "aria-label" in readme
    assert "全局关闭确认" in agents
    assert "aria-label" in agents
    assert "封面逐张加载" in readme
    assert "封面逐张加载" in agents


def test_gui_docs_cover_headless_window_regression() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "不可交互的白色窗口" in readme
    assert "--window-position=-32000,-32000" in agents
    assert "headed" in agents


def test_docs_define_complete_source_catalog_and_single_maintenance_point() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    expected_sources = {
        "netease": "网易云音乐",
        "migu": "咪咕音乐",
        "kugou": "酷狗音乐",
        "kuwo": "酷我音乐",
        "ytmusic": "YouTube Music",
        "tidal": "Tidal",
        "qobuz": "Qobuz",
        "deezer": "Deezer",
        "spotify": "Spotify",
        "tencent": "QQ音乐",
        "ximalaya": "喜马拉雅",
        "joox": "JOOX",
        "apple": "Apple Music",
    }
    for source_id, label in expected_sources.items():
        assert f"`{source_id}`" in readme
        assert label in readme

    assert "酷狗专辑搜索" in readme
    assert "上游不保证" in readme
    assert "CLI 参数仍使用音源 ID" in readme
    assert "音源只在 `music_downloader/domain/enums.py`" in agents
    assert "`VALID_SOURCES` 自动从 `Source` 派生" in agents
    assert "HTML、JSON 或 XML" in agents


def test_superseded_gui_docs_point_to_current_design() -> None:
    historical_docs = [
        ROOT / "docs/superpowers/plans/2026-07-02-vite-svelte-gui-refactor.md",
        ROOT / "docs/superpowers/specs/2026-07-02-vite-svelte-gui-refactor-design.md",
    ]

    for path in historical_docs:
        content = path.read_text(encoding="utf-8")
        assert "2026-07-12-music-workbench-frontend-design.md" in content
        assert "历史尺寸约定已被取代" in content
