import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "commit_seal.sh"


def git(repo, *a):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@localhost", *a], cwd=repo,
                          check=True, capture_output=True, text=True).stdout.strip()


def test_commit_seal_is_rerunnable_and_commits_only_the_seal(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "integration").mkdir()
    (tmp_path / "other.txt").write_text("x")
    git(tmp_path, "add", "other.txt")  # staged, must stay out of the seal commit
    seal = tmp_path / "integration" / "removal.seal"
    seal.write_text("abc\n")

    def run():
        return subprocess.run(["bash", str(SCRIPT), "integration/removal.seal"], cwd=tmp_path, capture_output=True,
                              text=True, env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@l",
                                              "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@l",
                                              "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"})

    assert run().returncode == 0
    assert git(tmp_path, "show", "--name-only", "--format=", "HEAD") == "integration/removal.seal"
    head = git(tmp_path, "rev-parse", "HEAD")
    again = run()
    assert again.returncode == 0 and git(tmp_path, "rev-parse", "HEAD") == head
    seal.write_text("def\n")
    assert run().returncode == 0 and git(tmp_path, "rev-parse", "HEAD") != head
