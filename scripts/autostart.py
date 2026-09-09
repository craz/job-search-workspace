#!/usr/bin/env python3
"""Install/uninstall/status for Job Search boot autostart (systemd).

Docker Compose ``restart:`` alone is NOT enough on this host: ``make up`` /
``make boot`` must start HH/Ollama unix-socket host bridges before Compose can
attach egress services. This helper installs a oneshot systemd unit that runs
``make boot``.

Install modes:

* root (``sudo make install-autostart``) → ``/etc/systemd/system/job-search.service``
* non-root → ``~/.config/systemd/user/job-search.service`` (``systemctl --user``)

For headless boot with a user unit, also run once:
``sudo loginctl enable-linger "$USER"``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIT_NAME = "job-search.service"
TEMPLATE = ROOT / "deploy" / "systemd" / "job-search.service.template"
SYSTEM_UNIT_DIR = Path("/etc/systemd/system")


def _run(cmd: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True, env=env)


def _make_bin() -> str:
    return shutil.which("make") or "/usr/bin/make"


def _user_unit_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def render_unit(*, workspace: Path, user: str, system: bool) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    text = (
        template.replace("@WORKSPACE@", str(workspace))
        .replace("@MAKE@", _make_bin())
        .replace(
            "@DOCKER_REQUIRES@",
            "After=docker.service\nRequires=docker.service" if system else "",
        )
        .replace("@USER_LINE@", f"User={user}" if system else "")
        .replace("@GROUP_LINE@", "Group=docker" if system else "")
        .replace("@WANTED_BY@", "multi-user.target" if system else "default.target")
    )
    # Drop empty placeholder lines left by user-mode omissions.
    lines = [line for line in text.splitlines() if line.strip() != ""]
    return "\n".join(lines) + "\n"


def install() -> int:
    if not TEMPLATE.is_file():
        print(f"missing template: {TEMPLATE}", file=sys.stderr)
        return 1
    system = os.geteuid() == 0
    user = os.environ.get("SUDO_USER") or os.environ.get("USER") or "root"
    if system:
        target = SYSTEM_UNIT_DIR / UNIT_NAME
        ctl = ["systemctl"]
    else:
        target_dir = _user_unit_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / UNIT_NAME
        ctl = ["systemctl", "--user"]
    unit_text = render_unit(workspace=ROOT, user=user, system=system)
    target.write_text(unit_text, encoding="utf-8")
    os.chmod(target, 0o644)
    _run([*ctl, "daemon-reload"])
    _run([*ctl, "enable", UNIT_NAME])
    mode = "system" if system else "user"
    print(f"installed and enabled ({mode}) {target}")
    print(f"workspace={ROOT} user={user}")
    if system:
        print("boot path: systemctl start job-search  (or machine reboot)")
    else:
        print("start now: systemctl --user start job-search")
        print('headless boot: sudo loginctl enable-linger "$USER"  (one-time)')
    return 0


def uninstall() -> int:
    system = os.geteuid() == 0
    removed = False
    if system or (SYSTEM_UNIT_DIR / UNIT_NAME).is_file():
        if os.geteuid() != 0 and (SYSTEM_UNIT_DIR / UNIT_NAME).is_file():
            print(
                "system unit present; uninstall with: sudo make uninstall-autostart",
                file=sys.stderr,
            )
            return 1
        if os.geteuid() == 0:
            _run(["systemctl", "disable", "--now", UNIT_NAME], check=False)
            target = SYSTEM_UNIT_DIR / UNIT_NAME
            if target.is_file():
                target.unlink()
                removed = True
            _run(["systemctl", "daemon-reload"], check=False)
    user_target = _user_unit_dir() / UNIT_NAME
    if user_target.is_file():
        _run(["systemctl", "--user", "disable", "--now", UNIT_NAME], check=False)
        user_target.unlink(missing_ok=True)
        _run(["systemctl", "--user", "daemon-reload"], check=False)
        removed = True
    print(f"removed {UNIT_NAME}" if removed else f"{UNIT_NAME} was not installed")
    return 0


def status() -> int:
    system_unit = SYSTEM_UNIT_DIR / UNIT_NAME
    user_unit = _user_unit_dir() / UNIT_NAME
    print(f"system_unit={'present' if system_unit.is_file() else 'absent'} path={system_unit}")
    print(f"user_unit={'present' if user_unit.is_file() else 'absent'} path={user_unit}")
    for label, ctl in (("system", ["systemctl"]), ("user", ["systemctl", "--user"])):
        enabled = _run([*ctl, "is-enabled", UNIT_NAME], check=False)
        active = _run([*ctl, "is-active", UNIT_NAME], check=False)
        print(
            f"{label}_enabled={enabled.stdout.strip() or enabled.returncode}"
        )
        print(
            f"{label}_active={active.stdout.strip() or active.returncode}"
        )
    unit = system_unit if system_unit.is_file() else user_unit
    if unit.is_file():
        for line in unit.read_text(encoding="utf-8").splitlines():
            if line.startswith(("WorkingDirectory=", "User=", "ExecStart=", "Type=")):
                print(line)
    return 0


def boot() -> int:
    """Canonical boot/start without image rebuild (used by systemd)."""
    os.chdir(ROOT)
    steps = [
        [sys.executable, str(ROOT / "scripts" / "host_http_proxy_socket.py"), "ensure"],
        [sys.executable, str(ROOT / "scripts" / "ollama_host_socket.py"), "ensure"],
    ]
    for cmd in steps:
        print("+", " ".join(cmd), flush=True)
        completed = subprocess.run(cmd, cwd=ROOT)
        if completed.returncode != 0:
            return completed.returncode
    compose_files = subprocess.check_output(
        [sys.executable, str(ROOT / "scripts" / "host_http_proxy_socket.py"), "compose-files"],
        cwd=ROOT,
        text=True,
    ).split()
    env = dict(os.environ)
    env.setdefault("COMPOSE_PROJECT_NAME", ROOT.name)
    # Remount egress sidecars onto current unix sockets, then bring the stack up.
    recreate = [
        "docker",
        "compose",
        *compose_files,
        "up",
        "-d",
        "--force-recreate",
        "--no-deps",
        "hh-egress",
        "ollama-egress",
    ]
    print("+", " ".join(recreate), flush=True)
    completed = subprocess.run(recreate, cwd=ROOT, env=env)
    if completed.returncode != 0:
        # ollama-egress may be absent when override is off — still start the stack.
        print("warning: egress recreate returned non-zero; continuing with compose up", flush=True)
    cmd = ["docker", "compose", *compose_files, "up", "-d"]
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT, env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "uninstall", "status", "boot"))
    args = parser.parse_args()
    if args.command == "install":
        return install()
    if args.command == "uninstall":
        return uninstall()
    if args.command == "status":
        return status()
    return boot()


if __name__ == "__main__":
    raise SystemExit(main())
