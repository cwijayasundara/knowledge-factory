import pytest


@pytest.fixture(autouse=True)
def _private_kf_home(monkeypatch, tmp_path_factory):
    """Starved runs write list copies under $KF_HOME/runs: never the real ~/.kf in tests."""
    monkeypatch.setenv("KF_HOME", str(tmp_path_factory.mktemp("kf-home")))
