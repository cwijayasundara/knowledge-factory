from datetime import UTC, datetime
from pathlib import Path

from kf.agent_tools import make_kf_tools
from kf.flags.models import FlagIn
from kf.flags.queue import FlagQueue

NOW = datetime(2026, 6, 1, tzinfo=UTC)


def tools(tmp_path: Path, run_id: str = "r"):
    return make_kf_tools(queue_path=tmp_path / "q.db", bundle_snapshot=tmp_path / "b", run_id=run_id,
                         agent_id="autorca", scenario="hero", now=lambda: NOW)


def test_kf_flag_writes_queue_only(tmp_path):
    t = make_kf_tools(queue_path=tmp_path/"q.db", bundle_snapshot=tmp_path/"b", run_id="r", agent_id="autorca", scenario="hero")
    out = t["kf_flag"].invoke({"kind": "missing", "summary": "alias TMS unknown"})
    assert "continue" in out.lower() and FlagQueue(tmp_path/"q.db").list()[0].run_id == "r"
    flag = FlagQueue(tmp_path / "q.db").list()[0]
    assert (flag.agent_id, flag.scenario, flag.kind.value) == ("autorca", "hero", "missing")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["q.db"]  # nothing written beside the queue


def test_kf_flag_args_match_flag_in(tmp_path):
    assert set(tools(tmp_path)["kf_flag"].args) == set(FlagIn.model_fields)


def test_kf_flag_records_optional_fields(tmp_path):
    tools(tmp_path)["kf_flag"].invoke({
        "kind": "stale", "summary": "s", "target": "domain/tms.md", "knowledge_type": "domain",
        "evidence": [{"resource": "raw/x.log", "excerpt": "e"}], "severity": "high"})
    f = FlagQueue(tmp_path / "q.db").list()[0]
    assert (f.target, f.knowledge_type.value, f.severity.value) == ("domain/tms.md", "domain", "high")
    assert f.evidence[0].resource == "raw/x.log"


def test_kf_flag_rate_limit_returns_notice_not_error(tmp_path):
    q = FlagQueue(tmp_path / "q.db")
    for i in range(20):
        q.add(FlagIn(kind="missing", summary=f"s{i}"), agent_id="autorca", run_id="r", scenario="hero")
    out = tools(tmp_path)["kf_flag"].invoke({"kind": "missing", "summary": "one more"})
    assert "limit" in out.lower() and "continue" in out.lower()
    assert len(q.list()) == 20


def test_kf_flag_invalid_flag_returns_notice_not_error(tmp_path):
    out = tools(tmp_path)["kf_flag"].invoke({"kind": "missing", "summary": "x" * 501})
    assert "not recorded" in out.lower() and FlagQueue(tmp_path / "q.db").list() == []


def test_kb_tools_have_no_write_path(tmp_path):
    assert set(tools(tmp_path)) == {"kf_flag", "kb_search", "kb_read"}


def test_kb_search_and_read_serve_the_snapshot(tmp_path):
    b = tmp_path / "b" / "domain"
    b.mkdir(parents=True)
    (b / "tms.md").write_text("---\ntitle: TMS alias\ndescription: d\n---\n# TMS\nTMS means tms-api\n")
    t = tools(tmp_path)
    found = t["kb_search"].invoke({"query": "tms"})
    assert "domain/tms.md" in found and "TMS alias" in found
    assert "tms-api" in t["kb_read"].invoke({"path": "domain/tms.md"})
    assert "no current knowledge" in t["kb_search"].invoke({"query": "zebra"}).lower()
    assert "bundle-relative" in t["kb_read"].invoke({"path": "../q.db"})


def test_kb_tool_descriptions_are_neutral(tmp_path):
    """The kb tools' model-facing text hints at no particular knowledge (the removal list's candidates)."""
    from langchain_core.utils.function_calling import convert_to_openai_tool
    import json

    t = tools(tmp_path)
    text = json.dumps([convert_to_openai_tool(t[n]) for n in ("kb_search", "kb_read")]).lower()
    for word in ("alias", "procedure", "trust", "field name"):
        assert word not in text, word
