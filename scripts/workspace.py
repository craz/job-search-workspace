#!/usr/bin/env python3
"""Manage and diagnose the Job Search Git-submodule workspace.

``bootstrap`` initializes only missing product submodules at the exact gitlink
commits recorded by the workspace. Existing checkouts are inspected but never
checked out, reset, cleaned, fetched, or switched, preserving user work.

``doctor`` verifies host tools, submodule declarations, gitlink revisions,
origins, worktree state, and optionally remote branch availability. The
workspace ``.gitmodules`` file is the repository manifest; Git's index stores
the compatible commit set, so no parallel lock file is maintained.

Result levels are OK, WARN, ERROR, and SKIP. ERROR produces exit code 1. Network
checks are bounded and can be disabled with ``doctor --offline``. This module
does not manage Compose, service data, releases, or remote writes.
"""

from __future__ import annotations

import argparse
import configparser
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
GITMODULES_PATH = WORKSPACE_ROOT / ".gitmodules"
REQUIRED_TOOLS = ("git", "docker", "direnv", "python3", "make")


@dataclass(frozen=True)
class Repository:
    """One independently versioned service declared as a Git submodule."""

    name: str
    path: str
    url: str
    branch: str


@dataclass(frozen=True)
class Check:
    """One diagnostic result with a stable severity, subject, and message."""

    level: str
    subject: str
    message: str


def load_repositories(gitmodules_path: Path = GITMODULES_PATH) -> list[Repository]:
    """Parse and validate service identity from ``.gitmodules``.

    Every section must be named ``submodule <name>`` and provide a unique path,
    URL, and explicit branch. Paths must stay below ``services/`` and may not be
    absolute or contain parent traversal. Invalid input fails before Git changes.
    """
    parser = configparser.ConfigParser(interpolation=None)
    with gitmodules_path.open(encoding="utf-8") as stream:
        parser.read_file(stream)

    repositories: list[Repository] = []
    seen_paths: set[str] = set()
    for section in parser.sections():
        if not section.startswith('submodule "') or not section.endswith('"'):
            raise ValueError(f"invalid .gitmodules section: {section}")
        name = section[len('submodule "') : -1]
        path = parser.get(section, "path", fallback="").strip()
        url = parser.get(section, "url", fallback="").strip()
        branch = parser.get(section, "branch", fallback="").strip()
        candidate = Path(path)
        if (
            not name
            or not path
            or not url
            or not branch
            or candidate.is_absolute()
            or ".." in candidate.parts
            or len(candidate.parts) != 2
            or candidate.parts[0] != "services"
        ):
            raise ValueError(f"invalid submodule declaration: {section}")
        if path in seen_paths:
            raise ValueError(f"duplicate submodule path: {path}")
        seen_paths.add(path)
        repositories.append(Repository(name=name, path=path, url=url, branch=branch))

    if not repositories:
        raise ValueError("no product submodules declared")
    return repositories


def run(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a bounded, non-shell child process and capture its text streams."""
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=timeout,
    )


def git(repo: Path, *args: str, check: bool = True) -> str:
    """Run Git against an explicit repository path and return stripped stdout."""
    result = run(("git", "-C", str(repo), *args), check=check)
    return result.stdout.strip()


def repository_path(workspace_root: Path, repository: Repository) -> Path:
    """Resolve one validated submodule path below the workspace root."""
    return workspace_root / repository.path


def recorded_commit(workspace_root: Path, repository: Repository) -> str:
    """Return the exact submodule commit stored as a mode-160000 gitlink."""
    output = git(workspace_root, "ls-files", "--stage", "--", repository.path)
    fields = output.split()
    if len(fields) < 3 or fields[0] != "160000" or len(fields[1]) != 40:
        raise ValueError(f"missing gitlink for {repository.path}")
    return fields[1]


def is_git_checkout(path: Path) -> bool:
    """Return whether Git recognizes ``path`` as an initialized worktree."""
    if not path.exists() or not (path / ".git").exists():
        return False
    result = run(("git", "-C", str(path), "rev-parse", "--is-inside-work-tree"), check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def bootstrap(repositories: Sequence[Repository], workspace_root: Path) -> list[Check]:
    """Initialize missing submodules and validate existing ones non-destructively.

    Only an absent or uninitialized checkout triggers ``git submodule update
    --init --recursive`` for that exact validated path. Existing Git worktrees
    are never updated automatically. Revision drift is a warning so local work
    remains available for review instead of being overwritten.
    """
    checks: list[Check] = []
    for repository in repositories:
        target = repository_path(workspace_root, repository)
        expected = recorded_commit(workspace_root, repository)
        if not is_git_checkout(target):
            if target.exists() and any(target.iterdir()):
                checks.append(Check("ERROR", repository.name, f"non-empty non-Git path: {target}"))
                continue
            run(
                (
                    "git",
                    "-C",
                    str(workspace_root),
                    "submodule",
                    "update",
                    "--init",
                    "--recursive",
                    "--",
                    repository.path,
                )
            )
            checks.append(Check("OK", repository.name, f"initialized at {repository.path}"))
        else:
            checks.append(Check("OK", repository.name, f"exists at {repository.path}"))

        origin = git(target, "remote", "get-url", "origin", check=False)
        if origin != repository.url:
            checks.append(Check("ERROR", repository.name, f"origin mismatch: {origin or '<missing>'}"))
            continue
        head = git(target, "rev-parse", "HEAD")
        level = "OK" if head == expected else "WARN"
        checks.append(Check(level, repository.name, f"HEAD {head[:12]} / gitlink {expected[:12]}"))
    return checks


def check_tools(*, skip_tools: bool) -> list[Check]:
    """Check required executables and Docker daemon availability."""
    if skip_tools:
        return [Check("SKIP", "tools", "host tool checks disabled")]
    checks: list[Check] = []
    for tool in REQUIRED_TOOLS:
        executable = shutil.which(tool)
        if executable is None:
            checks.append(Check("ERROR", tool, "not found in PATH"))
        else:
            checks.append(Check("OK", tool, executable))

    if shutil.which("docker"):
        result = run(("docker", "info"), check=False)
        if result.returncode == 0:
            checks.append(Check("OK", "docker-daemon", "reachable"))
        else:
            message = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unreachable"
            checks.append(Check("ERROR", "docker-daemon", message))
    return checks


def diagnose_repository(
    repository: Repository,
    workspace_root: Path,
    *,
    offline: bool,
) -> list[Check]:
    """Inspect one submodule without changing its revision or worktree."""
    target = repository_path(workspace_root, repository)
    if not is_git_checkout(target):
        return [Check("ERROR", repository.name, f"uninitialized submodule: {repository.path}")]

    expected = recorded_commit(workspace_root, repository)
    origin = git(target, "remote", "get-url", "origin", check=False)
    head = git(target, "rev-parse", "HEAD")
    status = git(target, "status", "--porcelain")
    checks = [
        Check(
            "OK" if origin == repository.url else "ERROR",
            repository.name,
            "origin matches" if origin == repository.url else f"origin mismatch: {origin}",
        ),
        Check(
            "OK" if head == expected else "ERROR",
            repository.name,
            f"HEAD {head[:12]} / gitlink {expected[:12]}",
        ),
        Check("OK" if not status else "WARN", repository.name, "clean" if not status else "dirty"),
    ]
    if offline:
        checks.append(Check("SKIP", repository.name, "remote check disabled"))
        return checks

    remote_environment = os.environ.copy()
    remote_environment["GIT_TERMINAL_PROMPT"] = "0"
    remote_environment["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o ConnectTimeout=10"
    try:
        remote = run(
            (
                "git",
                "-C",
                str(target),
                "ls-remote",
                "--exit-code",
                "origin",
                f"refs/heads/{repository.branch}",
            ),
            check=False,
            env=remote_environment,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        checks.append(Check("ERROR", repository.name, "remote check timed out after 15s"))
    else:
        message = remote.stderr.strip() or "remote branch is not reachable"
        checks.append(
            Check(
                "OK" if remote.returncode == 0 else "ERROR",
                repository.name,
                "remote branch reachable" if remote.returncode == 0 else message,
            )
        )
    return checks


def doctor(
    repositories: Sequence[Repository],
    workspace_root: Path,
    *,
    offline: bool,
    skip_tools: bool,
) -> list[Check]:
    """Collect host and submodule diagnostics without automatic repair."""
    checks = check_tools(skip_tools=skip_tools)
    for repository in repositories:
        checks.extend(diagnose_repository(repository, workspace_root, offline=offline))
    return checks


def print_checks(checks: Sequence[Check]) -> None:
    """Print stable ``[LEVEL] subject: message`` diagnostics."""
    for item in checks:
        print(f"[{item.level:<5}] {item.subject}: {item.message}")


def has_errors(checks: Sequence[Check]) -> bool:
    """Return whether any collected diagnostic is an error."""
    return any(item.level == "ERROR" for item in checks)


def build_parser() -> argparse.ArgumentParser:
    """Build the public bootstrap/doctor command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("bootstrap", help="initialize missing submodules and validate gitlinks")
    doctor_parser = subparsers.add_parser("doctor", help="validate tools, submodules and remotes")
    doctor_parser.add_argument("--offline", action="store_true", help="skip network remote checks")
    doctor_parser.add_argument("--skip-tools", action="store_true", help="skip host tool checks")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one workspace operation and return a CI-compatible exit code."""
    args = build_parser().parse_args(argv)
    try:
        repositories = load_repositories()
        if args.command == "bootstrap":
            checks = bootstrap(repositories, WORKSPACE_ROOT)
        else:
            checks = doctor(
                repositories,
                WORKSPACE_ROOT,
                offline=args.offline,
                skip_tools=args.skip_tools,
            )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"[ERROR] workspace: {error}", file=sys.stderr)
        return 1

    print_checks(checks)
    return 1 if has_errors(checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
