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
