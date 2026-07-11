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


def test_superseded_gui_docs_point_to_current_design() -> None:
    historical_docs = [
        ROOT / "docs/superpowers/plans/2026-07-02-vite-svelte-gui-refactor.md",
        ROOT / "docs/superpowers/specs/2026-07-02-vite-svelte-gui-refactor-design.md",
    ]

    for path in historical_docs:
        content = path.read_text(encoding="utf-8")
        assert "2026-07-12-music-workbench-frontend-design.md" in content
        assert "历史尺寸约定已被取代" in content
