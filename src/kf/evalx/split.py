"""Curation / held-out seed split (spec 9b): scenarios that feed the curator (flags, trails)
are generated from CURATION_SEEDS; scoring runs only on HELDOUT_SEEDS of the same families."""

CURATION_SEEDS: tuple[int, ...] = (11, 12, 13)
HELDOUT_SEEDS: tuple[int, ...] = (21, 22, 23)


def assert_disjoint(curation: tuple[int, ...] = CURATION_SEEDS,
                    heldout: tuple[int, ...] = HELDOUT_SEEDS) -> None:
    shared = sorted(set(curation) & set(heldout))
    if shared:
        raise ValueError(f"curation and held-out seeds overlap: {shared}")


assert_disjoint()

HELDOUT_ROOT = "data_heldout"


def is_heldout_path(path) -> bool:
    """True when `path` is under a data_heldout root, or is (or is inside) an eval run dir whose
    kf_run.json says held-out: held-out data must never reach the curator (spec 9b)."""
    import json
    from pathlib import Path

    p = Path(path).expanduser().resolve()
    if any(part.startswith(HELDOUT_ROOT) for part in p.parts):
        return True
    for d in (p, *p.parents):
        rec = d / "kf_run.json"
        if rec.is_file():
            try:
                return bool(json.loads(rec.read_text()).get("heldout"))
            except ValueError:
                return True  # unreadable: fail closed
    if p.is_dir():
        for rec in p.rglob("kf_run.json"):
            try:
                if json.loads(rec.read_text()).get("heldout"):
                    return True
            except ValueError:
                return True
    return False
