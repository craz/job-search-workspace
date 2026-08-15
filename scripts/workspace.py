#!/usr/bin/env python3
"""Управление Git-репозиториями Job Search multirepo workspace.

Скрипт предоставляет две безопасные начальные операции:

* ``bootstrap`` клонирует отсутствующие sibling-репозитории и проверяет уже
  существующие, не выполняя над ними fetch, checkout, reset или clean;
* ``doctor`` диагностирует инструменты хоста, Docker daemon, локальное состояние
  репозиториев и, если разрешено, доступность веток в remote.

Workspace определяется как каталог на уровень выше этого файла. Product repos
по умолчанию располагаются рядом с ним в ``WORKSPACE_ROOT.parent``. Manifest
``repos.yaml`` намеренно записан в JSON-синтаксисе (JSON является подмножеством
YAML), чтобы bootstrap обходился стандартной библиотекой Python. Произвольный
YAML-синтаксис этим скриптом не поддерживается.

Lock-файл сейчас является проверяемой спецификацией совместимых HEAD, но не
механизмом принудительного checkout. Даже новый clone получает текущий HEAD
указанной ветки, после чего скрипт сравнивает его с lock. Это сохраняет
недеструктивность, но означает, что bootstrap может завершиться с WARN при
изменившейся remote-ветке.

Уровни результатов: ERROR приводит к exit code 1; WARN и SKIP печатаются, но не
делают команду неуспешной. Ошибка разбора CLI остаётся стандартным exit code 2
от argparse. Скрипт пока не управляет Compose, сервисами, backup или restore —
эти операции появятся в workspace 0B вместе с реальными компонентами.
"""

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
    """Полное описание одного product repository.

    ``name``, ``path``, ``url``, ``branch``, ``visibility`` и ``role`` приходят
    из manifest. ``commit`` присоединяется из lock-файла. ``frozen=True`` не даёт
    случайно изменить проверяемую конфигурацию во время выполнения. Поля
    ``visibility`` и ``role`` пока являются метаданными и логикой не используются.
    """

    name: str
    path: str
    url: str
    branch: str
    visibility: str
    role: str
    commit: str


@dataclass(frozen=True)
class Check:
    """Результат одной независимой проверки.

    ``level`` принимает используемые CLI уровни OK, WARN, ERROR или SKIP;
    ``subject`` называет инструмент либо репозиторий; ``message`` объясняет
    результат. Только наличие ERROR меняет итоговый exit code на 1.
    """

    level: str
    subject: str
    message: str


def load_repositories(
    manifest_path: Path = MANIFEST_PATH,
    lock_path: Path = LOCK_PATH,
) -> list[Repository]:
    """Загрузить manifest и объединить его с точными версиями из lock-файла.

    Оба файла должны иметь ``schema_version == 1``. Имена в manifest обязаны
    быть уникальными; каждому имени нужна lock-запись с commit; лишние имена в
    lock запрещены. Нарушение контракта вызывает ``ValueError`` до любых Git
    операций. Отсутствующие файлы и неверный JSON передаются вызывающему коду как
    стандартные исключения чтения/декодирования.
    """
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
    """Запустить процесс без shell и вернуть захваченные stdout/stderr.

    Передача списка аргументов без shell исключает интерпретацию metacharacters.
    ``check=True`` превращает ненулевой exit code в ``CalledProcessError``;
    ``env`` позволяет задать изолированное окружение; ``timeout`` ограничивает
    выполнение только когда вызывающий код передал значение. Сейчас явный
    timeout используется для remote-check, но не для clone или ``docker info``.
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
    """Выполнить ``git -C <repo> ...`` и вернуть stdout без крайних пробелов.

    Явный ``-C`` делает результат независимым от текущего каталога процесса.
    При ``check=False`` вызывающий код сам интерпретирует exit code и stderr.
    """
    result = run(("git", "-C", str(repo), *args), check=check)
    return result.stdout.strip()


def repository_path(projects_dir: Path, repository: Repository) -> Path:
    """Получить путь checkout как ``projects_dir / manifest.path``."""
    return projects_dir / repository.path


def bootstrap(repositories: Sequence[Repository], projects_dir: Path) -> list[Check]:
    """Клонировать отсутствующие репозитории и проверить существующие.

    Отсутствующий target клонируется с ``--branch`` и ``--single-branch``.
    Существующий каталог без ``.git`` даёт ERROR и никогда не перезаписывается.
    Для Git checkout проверяются origin и HEAD. Несовпадение origin — ERROR;
    несовпадение HEAD с lock — WARN, поскольку функция принципиально не делает
    fetch, checkout, reset или clean и сохраняет пользовательскую работу.

    Важно: clone следует текущему HEAD remote-ветки и не checkout-ит lock commit.
    Поэтому lock здесь обнаруживает drift, но не гарантирует его исправление.
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
    """Проверить host executables и доступность Docker daemon.

    ``shutil.which`` ищет Git, Docker, direnv, Python и Make. Если Docker CLI
    найден, ``docker info`` отличает установленный клиент от доступного daemon.
    ``skip_tools`` используется для изолированных тестов репозиторной логики и
    возвращает явный SKIP, а не притворный успешный результат.
    """
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
    """Диагностировать один checkout, не изменяя его состояние.

    Проверяются наличие ``.git``, точное совпадение origin, равенство HEAD lock,
    чистота worktree и существование configured branch в remote. В doctor drift
    HEAD является ERROR, а dirty worktree — WARN: изменения не мешают диагностике
    и никогда автоматически не удаляются.

    В offline-режиме сеть заменяется явным SKIP. Иначе ``git ls-remote`` получает
    ``GIT_TERMINAL_PROMPT=0``, SSH BatchMode, SSH connect timeout 10 секунд и
    общий process timeout 15 секунд. Проверка подтверждает доступность ветки, но
    не сравнивает SHA remote-ветки с lock.
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
    """Собрать проверки хоста и всех manifest repositories в один список.

    Функция сохраняет все результаты, чтобы пользователь увидел все проблемы за
    один запуск, а не только первую ошибку. Никакие исправления не выполняются.
    """
    checks = check_tools(skip_tools=skip_tools)
    for repository in repositories:
        checks.extend(diagnose_repository(repository, projects_dir, offline=offline))
    return checks


def print_checks(checks: Sequence[Check]) -> None:
    """Напечатать стабильный ``[LEVEL] subject: message`` для терминала и CI."""
    for item in checks:
        print(f"[{item.level:<5}] {item.subject}: {item.message}")


def has_errors(checks: Sequence[Check]) -> bool:
    """Вернуть True, если хотя бы один Check имеет уровень ERROR."""
    return any(item.level == "ERROR" for item in checks)


def build_parser() -> argparse.ArgumentParser:
    """Описать CLI, help-тексты и допустимые комбинации аргументов.

    ``--projects-dir`` является глобальным аргументом и поэтому указывается до
    subcommand. ``--offline`` и ``--skip-tools`` принадлежат только doctor.
    Обязательный subcommand обеспечивает стандартную argparse-ошибку с code 2.
    """
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
    """Выполнить выбранную операцию и вернуть процессный exit code.

    Manifest загружается до выбора операции. Ожидаемые ошибки файлов, схемы и
    subprocess переводятся в одно диагностическое сообщение и code 1. После
    успешного выполнения печатаются все Check: ERROR даёт 1, а отсутствие ERROR
    даёт 0 даже при WARN или SKIP. Ошибки argparse обрабатываются до этой функции.
    """
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
