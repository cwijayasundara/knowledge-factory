import pytest
from pydantic import ValidationError

from kf.cli import main
from kf.evalx.removal import RemovalItem, RemovalList, seal, seed_overlaps, verify_seal

SAMPLE = """items:
  - id: alias-hints
    file: prompts/autorca.md
    match: "checkout is also called co-svc"
    why_derivable_from: "catalog: raw/catalog/apps.yaml lists the alias"
"""
ITEM = {"id": "a", "file": "prompts/autorca.md", "match": "x", "why_derivable_from": "catalog"}


def test_seal_detects_edit(tmp_path):
    p, s = tmp_path / "r.yaml", tmp_path / "removal.seal"
    p.write_text(SAMPLE)
    h = seal(p, s)
    assert len(h) == 64 and s.read_text().strip() == h and verify_seal(p, s)
    p.write_text(SAMPLE + "\n# tweak")
    assert not verify_seal(p, s)


def test_verify_without_a_seal_is_false(tmp_path):
    p = tmp_path / "r.yaml"
    p.write_text(SAMPLE)
    assert not verify_seal(p, tmp_path / "missing.seal")


def test_load_reads_items(tmp_path):
    p = tmp_path / "r.yaml"
    p.write_text(SAMPLE)
    (item,) = RemovalList.load(p).items
    assert item.id == "alias-hints" and item.file == "prompts/autorca.md"


def test_template_with_no_items_loads(tmp_path):
    p = tmp_path / "r.yaml"
    p.write_text("# only a comment\nitems: []\n")
    assert RemovalList.load(p).items == []


@pytest.mark.parametrize("missing", ["id", "file", "match", "why_derivable_from"])
def test_item_without_a_required_field_rejected(missing):
    with pytest.raises(ValidationError):
        RemovalItem(**{k: v for k, v in ITEM.items() if k != missing})


def test_item_without_derivation_rejected():
    with pytest.raises(ValidationError):
        RemovalItem(**{**ITEM, "why_derivable_from": ""})


def test_item_file_must_name_a_prompt():
    with pytest.raises(ValidationError):
        RemovalItem(**{**ITEM, "file": "src/e2ekg/agent/tools.py"})


def test_duplicate_ids_rejected():
    with pytest.raises(ValidationError):
        RemovalList(items=[ITEM, ITEM])


def test_seal_refuses_an_invalid_list(tmp_path):
    p, s = tmp_path / "r.yaml", tmp_path / "removal.seal"
    p.write_text("items:\n  - id: a\n    file: prompts/autorca.md\n    match: x\n")
    with pytest.raises(ValidationError):
        seal(p, s)
    assert not s.exists()


def test_cli_seal_and_verify(tmp_path, capsys):
    p, s = tmp_path / "r.yaml", tmp_path / "removal.seal"
    p.write_text(SAMPLE)
    args = ["seal", "--list", str(p), "--seal-file", str(s)]
    assert main(args) == 0
    assert capsys.readouterr().out.strip() == s.read_text().strip()
    assert main([*args, "--verify"]) == 0
    p.write_text(SAMPLE + "# tweak\n")
    assert main([*args, "--verify"]) == 1


def _removal(tmp_path, match="checkout is also called co-svc"):
    p = tmp_path / "r.yaml"
    p.write_text(f'items:\n  - id: alias-hints\n    file: prompts/autorca.md\n    match: "{match}"\n'
                 '    why_derivable_from: "catalog"\n  - id: other\n    file: prompts/autorca.md\n'
                 '    match: "never in the bundle"\n    why_derivable_from: "logs"\n')
    return p


def test_seed_overlaps_names_items_found_in_any_bundle_file_normalized(tmp_path):
    b = tmp_path / "bundle"
    (b / "domain").mkdir(parents=True)
    (b / "domain" / "a.md").write_text("Note: Checkout\n  is ALSO called   co-svc in chat.\n")
    assert seed_overlaps(b, RemovalList.load(_removal(tmp_path))) == ["alias-hints"]


def test_seed_overlaps_is_empty_for_a_disjoint_bundle(tmp_path):
    b = tmp_path / "bundle"
    b.mkdir()
    (b / "a.md").write_text("severity definitions only\n")
    assert seed_overlaps(b, RemovalList.load(_removal(tmp_path))) == []


def _overlapping(tmp_path):
    p = _removal(tmp_path)
    b = tmp_path / "bundle"
    b.mkdir()
    (b / "a.md").write_text("checkout is also called co-svc\n")
    return p, b


def test_seal_refuses_with_exit_1_when_the_seed_overlaps(tmp_path, capsys):
    p, b = _overlapping(tmp_path)
    s = tmp_path / "removal.seal"
    assert main(["seal", "--list", str(p), "--seal-file", str(s), "--bundle", str(b)]) == 1
    assert "alias-hints" in capsys.readouterr().err and not s.exists()


def test_heldout_eval_refuses_overlap_but_test_run_does_not(tmp_path, capsys, monkeypatch):
    from kf.evalx import cli as evalx_cli

    p, b = _overlapping(tmp_path)
    calls = []
    monkeypatch.setattr(evalx_cli, "run_eval", lambda **kw: calls.append(kw) or kw["run_dir"])
    base = ["eval", "run", "--heldout", "--list", str(p), "--bundle", str(b), "--state-dir", str(tmp_path / "st")]
    assert main(base) == 1 and not calls
    assert "alias-hints" in capsys.readouterr().err
    assert main([*base, "--test-run"]) == 0 and calls
