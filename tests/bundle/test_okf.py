from datetime import UTC, datetime

from kf.bundle.okf import dump_concept, is_human_reviewed, load_concept, stamp_verified

GEN = {"by": "kf-curator/0.1", "at": "2026-11-22T02:00:00Z"}


def test_human_reviewed_requires_human_after_generated():
    f = {"generated": GEN, "verified": [{"by": "human:ana", "at": "2026-11-21T10:00:00Z"}]}
    assert not is_human_reviewed(f)
    stamped = stamp_verified(f, "human:ana", datetime(2026, 11, 23, tzinfo=UTC))
    assert is_human_reviewed(stamped)
    assert len(stamped["verified"]) == 2 and len(f["verified"]) == 1


def test_non_human_verified_is_not_human_reviewed():
    f = {"generated": GEN, "verified": [{"by": "team:data", "at": "2026-11-23T00:00:00Z"}]}
    assert not is_human_reviewed(f)


def test_roundtrip_keeps_unknown_keys_and_history(tmp_path):
    src = (
        "---\ntitle: T\nx-foo: {a: 1}\ngenerated: {by: kf-curator/0.1, at: 2026-11-22T02:00:00Z}\n"
        "verified:\n- {by: human:ana, at: 2026-11-21T10:00:00Z}\n---\n# Body\n\ntext\n"
    )
    p = tmp_path / "c.md"
    p.write_text(src)
    c = load_concept(p)
    assert c.front["x-foo"] == {"a": 1}
    assert c.front["verified"][0]["at"] == "2026-11-21T10:00:00Z"
    out = dump_concept(c)
    p.write_text(out)
    c2 = load_concept(p)
    assert c2.front == c.front and c2.body == c.body
