#!/usr/bin/env python3
"""Keep a Claude Code session inside its own repository unless the owner approves.

Run by Claude Code before every Edit, Write, NotebookEdit and Bash call
(.claude/settings.json). It reads the tool call as JSON on stdin and prints
nothing for a call that stays inside this repository. For a call that would
change something elsewhere it prints a "permissionDecision": "ask", so the
owner is shown a permission prompt and decides; the session cannot approve it
for itself.

Inside this repository means: the project folder and any git worktree of the
same repository. Scratch space (the system temp folder and ~/.claude) may also
be written, except inside another repository's work tree there. Changing
something elsewhere means:
- editing or writing a file in another repository, or outside this repository
  and scratch space;
- a git command that changes history or branches (commit, push, merge, rebase,
  reset, checkout, switch, branch -d/-D, tag, worktree, stash, cherry-pick,
  revert, am, apply) run in another folder (`cd <dir>` or `git -C <dir>`);
- a git push to a URL that is not this repository's;
- a GitHub change (`gh pr create/merge/close/edit/review/comment`,
  `gh issue create/close/edit/comment`, `gh repo`, `gh release`, or
  `gh api` with a writing method or fields) aimed at another repository.
Reading anything, anywhere, is never stopped.

This is a guard against mistakes, not a sandbox: a determined shell command can
get around it. The rule it backs is in CLAUDE.md.

Copyright 2026 Harrison Cormier, Ashley Pacek and Varvara Blinova.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

GIT_WRITES = {"commit", "push", "merge", "rebase", "reset", "checkout", "switch",
              "tag", "worktree", "stash", "cherry-pick", "revert", "am", "apply",
              "pull", "branch"}
GH_WRITES = {("pr", "create"), ("pr", "merge"), ("pr", "close"), ("pr", "edit"),
             ("pr", "review"), ("pr", "comment"), ("pr", "ready"), ("pr", "reopen"),
             ("issue", "create"), ("issue", "close"), ("issue", "edit"),
             ("issue", "comment"), ("issue", "reopen"), ("issue", "delete")}
GH_WRITE_GROUPS = {"repo", "release", "secret", "variable", "workflow", "label"}
_PREFIX_WORDS = {"do", "then", "else", "elif", "time", "env", "xargs", "nohup", "command",
                 "exec", "!", "{", "("}
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _run(args, cwd):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                              timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _real(path, base):
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(base, path)
    return os.path.realpath(path)


def _inside(path, roots):
    return any(path == r or path.startswith(r.rstrip(os.sep) + os.sep) for r in roots)


def git_root(path):
    """The work tree that holds `path` (walking up to an existing folder), or None."""
    d = path
    while d and not os.path.isdir(d):
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent
    out = _run(["git", "rev-parse", "--show-toplevel"], d).strip()
    return os.path.realpath(out) if out else None


def outside(path, roots):
    """True when a change at `path` is outside this repository: inside another
    git work tree, or outside both this repository and scratch space."""
    if _inside(path, roots):
        return False
    other = git_root(path)
    if other and other not in roots:
        return True
    return not _inside(path, scratch_roots())


def repo_roots(project):
    roots = {os.path.realpath(project)}
    for line in _run(["git", "worktree", "list", "--porcelain"], project).splitlines():
        if line.startswith("worktree "):
            roots.add(os.path.realpath(line[len("worktree "):]))
    return roots


def scratch_roots():
    return {os.path.realpath(tempfile.gettempdir()), os.path.realpath("/tmp"),
            os.path.realpath(os.path.expanduser("~/.claude"))}


def github_name(project):
    url = _run(["git", "remote", "get-url", "origin"], project).strip()
    m = re.search(r"github\.com[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
    if m:
        return f"{m.group(1)}/{m.group(2)}".lower()
    m = re.search(r"/git/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}".lower() if m else None


def _segments(command):
    """Split a shell command into simple commands at ; && || | and newlines."""
    parts = re.split(r"\s*(?:;|&&|\|\||\||\n)\s*", command)
    out = []
    for p in parts:
        try:
            words = shlex.split(p, comments=True)
        except ValueError:
            words = p.split()
        while words and (words[0] in _PREFIX_WORDS or _ASSIGN_RE.match(words[0])):
            words = words[1:]
        if words:
            out.append(words)
    return out


def _other_repo_in(words, here):
    """A GitHub owner/name this command names that is not this repository."""
    names = []
    for i, w in enumerate(words):
        if w in ("--repo", "-R") and i + 1 < len(words):
            names.append(words[i + 1])
        elif w.startswith("--repo="):
            names.append(w.split("=", 1)[1])
        for m in re.finditer(r"repos/([^/\s]+)/([^/\s?]+)", w):
            names.append(f"{m.group(1)}/{m.group(2)}")
        for m in re.finditer(r"github\.com[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?(?:/|$)", w):
            names.append(f"{m.group(1)}/{m.group(2)}")
    for n in names:
        n = n.lower().removesuffix(".git").strip("/")
        if here is None or n != here:
            return n
    return None


def bash_reason(command, project, roots, here):
    cwd = os.path.realpath(project)
    for words in _segments(command):
        if words[0] == "cd" and len(words) > 1:
            cwd = _real(words[1], cwd)
            continue
        if words[0] == "git":
            where, i = cwd, 1
            while i < len(words) and words[i].startswith("-"):
                if words[i] == "-C" and i + 1 < len(words):
                    where = _real(words[i + 1], where)
                    i += 2
                    continue
                i += 2 if words[i] in ("-c", "--git-dir", "--work-tree") else 1
            sub = words[i] if i < len(words) else ""
            if sub not in GIT_WRITES:
                continue
            if sub == "branch" and not any(w in ("-d", "-D", "-m", "-M", "--delete")
                                           for w in words[i + 1:]):
                continue
            root = git_root(where)
            if (root not in roots) if root else outside(where, roots):
                return f"git {sub} in {where}, which is outside this repository"
            if sub == "push":
                other = _other_repo_in(words[i + 1:], here)
                if other:
                    return f"git push to {other}, which is not this repository"
        if words[0] == "gh" and len(words) > 1:
            group = words[1]
            action = words[2] if len(words) > 2 else ""
            writing = (group, action) in GH_WRITES or group in GH_WRITE_GROUPS
            if group == "api":
                method = None
                for j, w in enumerate(words):
                    if w in ("-X", "--method") and j + 1 < len(words):
                        method = words[j + 1].upper()
                    elif w.startswith("--method="):
                        method = w.split("=", 1)[1].upper()
                has_fields = any(w in ("-f", "-F", "--field", "--raw-field", "--input")
                                 for w in words)
                writing = (method or ("POST" if has_fields else "GET")) != "GET"
            if not writing:
                continue
            other = _other_repo_in(words[2:], here)
            if other is None and (git_root(cwd) or cwd) not in roots:
                other = f"the repository in {cwd}"
            if other:
                what = "api" if group == "api" else f"{group} {action}"
                return f"gh {what} on {other}, which is not this repository"
    return None


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0
    project = os.environ.get("CLAUDE_PROJECT_DIR") or call.get("cwd") or os.getcwd()
    roots = repo_roots(project)
    tool = call.get("tool_name", "")
    args = call.get("tool_input") or {}
    reason = None
    if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
        path = args.get("file_path") or args.get("notebook_path")
        if path and outside(_real(path, project), roots):
            reason = f"{tool} of {path}, which is outside this repository"
    elif tool == "Bash":
        reason = bash_reason(args.get("command") or "", project, roots, github_name(project))
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason":
                f"Outside this repository: {reason}. CLAUDE.md, 'Stay in this "
                "repository': this needs the owner's approval."}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
