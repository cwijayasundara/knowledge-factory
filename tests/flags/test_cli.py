from kf.cli import main
from kf.flags.models import FlagIn, FlagStatus
from kf.flags.queue import FlagQueue


def test_flags_list_status(tmp_path, capsys):
    db = tmp_path / "q.db"
    q = FlagQueue(db)
    a = q.add(FlagIn(kind="stale", summary="one"), agent_id="a", run_id="r", scenario="s")
    q.add(FlagIn(kind="missing", summary="two"), agent_id="a", run_id="r", scenario="s")
    q.set_status(a.id, FlagStatus.held)
    assert main(["flags", "list", "--db", str(db), "--status", "held"]) == 0
    out = capsys.readouterr().out
    assert "one" in out and "two" not in out
