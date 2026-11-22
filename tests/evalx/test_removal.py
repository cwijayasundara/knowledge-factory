import pytest
from pydantic import ValidationError

from kf.cli import main
from kf.evalx.removal import RemovalItem, RemovalList, seal, verify_seal

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
