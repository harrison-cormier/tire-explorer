"""scripts/guard_repo_boundary.py asks the owner before a session changes
anything outside its own repository, and stays silent for everything else.

Copyright 2026 Harrison Cormier, Ashley Pacek and Varvara Blinova.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[1] / "scripts" / "guard_repo_boundary.py"


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repos(tmp_path):
    here = tmp_path / "here"
    other = tmp_path / "other"
    for d in (here, other):
        d.mkdir()
        _git("init", "-q", "-b", "main", cwd=d)
        _git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
             "--allow-empty", "-m", "start", cwd=d)
    _git("remote", "add", "origin", "https://github.com/owner/here.git", cwd=here)
    _git("worktree", "add", "-q", "-b", "side", str(tmp_path / "here-side"), cwd=here)
    return here, other, tmp_path / "here-side"


def _ask(call, project):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
    out = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(call),
                         capture_output=True, text=True, env=env, check=True).stdout
    if not out.strip():
        return None
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "ask"
    return decision["permissionDecisionReason"]


def _edit(path):
    return {"tool_name": "Edit", "tool_input": {"file_path": str(path)}}


def _bash(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_edits_inside_the_repository_its_worktrees_and_scratch_are_silent(repos):
    here, _, side = repos
    assert _ask(_edit(here / "README.md"), here) is None
    assert _ask(_edit("docs/notes.md"), here) is None
    assert _ask(_edit(side / "README.md"), here) is None
    assert _ask(_edit("/tmp/scratch/notes.md"), here) is None


def test_an_edit_in_another_folder_asks_the_owner(repos):
    here, other, _ = repos
    assert "outside this repository" in _ask(_edit(other / "README.md"), here)
    assert _ask(_edit(f"{here}/../other/CLAUDE.md"), here)


def test_git_changes_elsewhere_ask_and_reads_do_not(repos):
    here, other, side = repos
    assert _ask(_bash(f"git -C {other} log -1"), here) is None
    assert _ask(_bash("git status && git commit -qm x"), here) is None
    assert _ask(_bash(f"cd {side} && git commit -qm x"), here) is None
    assert _ask(_bash(f"git -C {other} commit -m x"), here)
    assert _ask(_bash(f"cd {other} && git push -u origin x"), here)
    assert _ask(_bash(f"GIT_AUTHOR_NAME=x git -C {other} commit -m y"), here)
    assert _ask(_bash("git push https://github.com/owner/else.git HEAD"), here)
    assert _ask(_bash("git push -u origin side"), here) is None


def test_github_changes_to_another_repository_ask(repos):
    here, _, _ = repos
    assert _ask(_bash("gh api repos/owner/here/pulls -f title=x"), here) is None
    assert _ask(_bash("gh pr create --title x --body y"), here) is None
    assert _ask(_bash("gh api repos/owner/else/pulls --jq .[].number"), here) is None
    assert _ask(_bash("gh api repos/owner/else/pulls -f title=x"), here)
    assert _ask(_bash("gh api -X PUT repos/owner/else/pulls/1/merge"), here)
    assert _ask(_bash("gh pr merge 3 --repo owner/else"), here)
    assert _ask(_bash("for r in a b; do gh api -X PUT repos/owner/$r/pulls/1/merge; done"), here)


def test_input_it_cannot_read_is_left_alone(repos):
    here, _, _ = repos
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(here))
    out = subprocess.run([sys.executable, str(GUARD)], input="not json",
                         capture_output=True, text=True, env=env, check=True).stdout
    assert out == ""
