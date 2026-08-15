#!/usr/bin/env python3
"""Bootstrap and diagnose the Job Search multirepo workspace."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECTS_DIR = WORKSPACE_ROOT.parent
MANIFEST_PATH = WORKSPACE_ROOT / "repos.yaml"
LOCK_PATH = WORKSPACE_ROOT / "repos.lock.json"
REQUIRED_TOOLS = ("git", "docker", "direnv", "python3", "make")


@dataclass(frozen=True)
class Repository:
    """One product repository resolved from the manifest and version lock."""

    name: str
    path: str
    url: str
    branch: str
    visibility: str
    role: str
    commit: str


@dataclass(frozen=True)
class Check:
    """A diagnostic result whose level controls the command exit status."""

    level: str
    subject: str
    message: str


def load_repositories(
    manifest_path: Path = MANIFEST_PATH,
    lock_path: Path = LOCK_PATH,
) -> list[Repository]:
    """Load the JSON-compatible YAML manifest and machine lock file."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))

    if manifest.get("schema_version") != 1 or lock.get("schema_version") != 1:
        raise ValueError("unsupported workspace schema_version")

    locked = lock.get("repositories", {})
    repositories: list[Repository] = []
    seen: set[str] = set()
    for item in manifest.get("repositories", []):
        name = item["name"]
        if name in seen:
            raise ValueError(f"duplicate repository: {name}")
        seen.add(name)
        if name not in locked or "commit" not in locked[name]:
            raise ValueError(f"missing lock entry: {name}")
        repositories.append(
            Repository(
                name=name,
                path=item["path"],
                url=item["url"],
                branch=item["branch"],
                visibility=item["visibility"],
                role=item["role"],
                commit=locked[name]["commit"],
            )
        )

    extra_locks = set(locked) - seen
    if extra_locks:
        raise ValueError(f"lock contains unknown repositories: {sorted(extra_locks)}")
    return repositories


def run(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a bounded child process and capture output for stable diagnostics.

    Callers choose whether a non-zero exit raises. A timeout always raises so a
    network or credential prompt cannot silently freeze automation.
    """
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
    """Run Git against an explicit checkout and return normalized stdout."""
    result = run(("git", "-C", str(repo), *args), check=check)
    return result.stdout.strip()


def repository_path(projects_dir: Path, repository: Repository) -> Path:
    """Resolve a manifest-relative checkout without relying on the shell CWD."""
    return projects_dir / repository.path


def bootstrap(repositories: Sequence[Repository], projects_dir: Path) -> list[Check]:
    """Clone missing repositories and safely validate existing checkouts.

    Existing repositories are never fetched, reset, cleaned or checked out: the
    worktree may contain user changes. Version drift is only reported.
    """
    projects_dir.mkdir(parents=True, exist_ok=True)
    checks: list[Check] = []
    for repository in repositories:
        target = repository_path(projects_dir, repository)
        if not target.exists():
            run(
                (
                    "git",
                    "clone",
                    "--branch",
                    repository.branch,
                    "--single-branch",
                    repository.url,
                    str(target),
                )
            )
            checks.append(Check("OK", repository.name, f"cloned to {target}"))
        elif not (target / ".git").exists():
            checks.append(Check("ERROR", repository.name, f"not a Git repository: {target}"))
            continue
        else:
            checks.append(Check("OK", repository.name, f"exists at {target}"))

        origin = git(target, "remote", "get-url", "origin", check=False)
        if origin != repository.url:
            checks.append(
                Check("ERROR", repository.name, f"origin mismatch: {origin or '<missing>'}")
            )
            continue
        head = git(target, "rev-parse", "HEAD")
        if head == repository.commit:
            checks.append(Check("OK", repository.name, f"locked at {head[:12]}"))
        else:
            checks.append(
                Check(
                    "WARN",
                    repository.name,
                    f"HEAD {head[:12]} differs from lock {repository.commit[:12]}",
                )
            )
    return checks


def check_tools(*, skip_tools: bool) -> list[Check]:
    """Check required host executables and verify that Docker is usable."""
    if skip_tools:
        return [Check("SKIP", "tools", "host tool checks disabled")]
    checks: list[Check] = []
    for tool in REQUIRED_TOOLS:
        executable = shutil.which(tool)
        if executable is None:
            checks.append(Check("ERROR", tool, "not found in PATH"))
            continue
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
    projects_dir: Path,
    *,
    offline: bool,
) -> list[Check]:
    """Validate identity, revision, cleanliness and remote reachability.

    Remote access disables terminal prompts and uses bounded timeouts so doctor
    remains safe for unattended development flows.
    """
    target = repository_path(projects_dir, repository)
    if not (target / ".git").exists():
        return [Check("ERROR", repository.name, f"missing repository: {target}")]

    checks: list[Check] = []
    origin = git(target, "remote", "get-url", "origin", check=False)
    checks.append(
        Check(
            "OK" if origin == repository.url else "ERROR",
            repository.name,
            "origin matches" if origin == repository.url else f"origin mismatch: {origin}",
        )
    )

    head = git(target, "rev-parse", "HEAD")
    checks.append(
        Check(
            "OK" if head == repository.commit else "ERROR",
            repository.name,
            f"HEAD {head[:12]} / lock {repository.commit[:12]}",
        )
    )

    status = git(target, "status", "--porcelain")
    checks.append(
        Check("OK" if not status else "WARN", repository.name, "clean" if not status else "dirty")
    )

    if offline:
        checks.append(Check("SKIP", repository.name, "remote check disabled"))
    else:
        remote_environment = os.environ.copy()
        remote_environment["GIT_TERMINAL_PROMPT"] = "0"
        remote_environment["GIT_SSH_COMMAND"] = (
            "ssh -o BatchMode=yes -o ConnectTimeout=10"
        )
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
    projects_dir: Path,
    *,
    offline: bool,
    skip_tools: bool,
) -> list[Check]:
    """Collect host and repository diagnostics without changing the workspace."""
    checks = check_tools(skip_tools=skip_tools)
    for repository in repositories:
        checks.extend(diagnose_repository(repository, projects_dir, offline=offline))
    return checks


def print_checks(checks: Sequence[Check]) -> None:
    """Render checks consistently for humans and CI logs."""
    for item in checks:
        print(f"[{item.level:<5}] {item.subject}: {item.message}")


def has_errors(checks: Sequence[Check]) -> bool:
    """Return whether diagnostics require a failing process exit code."""
    return any(item.level == "ERROR" for item in checks)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI contract for bootstrap and doctor operations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=DEFAULT_PROJECTS_DIR,
        help=f"parent directory for repositories (default: {DEFAULT_PROJECTS_DIR})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("bootstrap", help="clone missing repositories and validate origins")
    doctor_parser = subparsers.add_parser("doctor", help="validate tools, repositories and remotes")
    doctor_parser.add_argument("--offline", action="store_true", help="skip network remote checks")
    doctor_parser.add_argument("--skip-tools", action="store_true", help="skip host tool checks")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute a command and translate expected operational failures to exit 1."""
    args = build_parser().parse_args(argv)
    try:
        repositories = load_repositories()
        if args.command == "bootstrap":
            checks = bootstrap(repositories, args.projects_dir.resolve())
        else:
            checks = doctor(
                repositories,
                args.projects_dir.resolve(),
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
