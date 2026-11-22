import json

import pytest

from kf.cli import main
from kf.curator.guard import WriteDenied, WriteGuard
from kf.curator.ontology_handoff import PROPOSE_COMMAND, OntologyNeed, file_ontology_need
from kf.curator.tools import CuratorError, CuratorTools, build_curator_tools


@pytest.fixture
def tools(repo, queue, raw_dir, tmp_path):
    t = CuratorTools(repo, "kf/r1", queue, raw_dir, WriteGuard.default(), state_dir=tmp_path / "state")
    t.open_branch()
    return t


def test_need_file_written(tmp_path):
    p = file_ontology_need(OntologyNeed(flag_ids=[1], kind="error_template", example="conn refused"),
                           out_dir=tmp_path / "needs")
    assert p.parent == tmp_path / "needs" and p.suffix == ".json"
    assert json.loads(p.read_text()) == {"id": 1, "flag_ids": [1], "kind": "error_template",
                                         "example": "conn refused"}
    p2 = file_ontology_need(OntologyNeed(flag_ids=[], kind="metric_tag", example="k"), out_dir=tmp_path / "needs")
    assert p2 != p


@pytest.mark.parametrize("path", ["ontology/extensions/x.ttl", "ontology/x.md", "bundle/domain/x.ttl", "a/b.ttl"])
def test_curator_has_no_turtle_write(path):
    with pytest.raises(WriteDenied):
        WriteGuard.default().check(path)


def test_tool_files_need_and_records_it(tools, tmp_path):
    tools.list_flags()
    out = build_curator_tools(tools)["file_ontology_need"].invoke(
        {"flag_ids": [1], "kind": "error_template", "example": "pool exhausted"})
    assert "filed" in out
    assert (tmp_path / "state" / "ontology_needs" / "001.json").is_file()
    assert tools.record["ontology_needs"] == ["001.json"]


def test_tool_rejects_bad_kind_and_foreign_flag(tools):
    tools.list_flags()
    with pytest.raises(CuratorError):
        tools.file_ontology_need([1], "turtle", "x")
    with pytest.raises(CuratorError):
        tools.file_ontology_need([99], "metric_tag", "x")


def test_cli_prints_needs_and_command(tmp_path, capsys):
    file_ontology_need(OntologyNeed(flag_ids=[2], kind="event_type", example="deploy:rollback"),
                       out_dir=tmp_path / "ontology_needs")
    assert main(["ontology-needs", "--state-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "event_type" in out and "deploy:rollback" in out and PROPOSE_COMMAND in out
