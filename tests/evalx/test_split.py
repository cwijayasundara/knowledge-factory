import pytest

from kf.evalx.split import CURATION_SEEDS, HELDOUT_SEEDS, assert_disjoint


def test_seed_sets_disjoint():
    assert CURATION_SEEDS and HELDOUT_SEEDS
    assert not set(CURATION_SEEDS) & set(HELDOUT_SEEDS)
    assert_disjoint()


def test_assert_disjoint_rejects_overlap():
    with pytest.raises(ValueError, match="12"):
        assert_disjoint((11, 12), (12, 21))
