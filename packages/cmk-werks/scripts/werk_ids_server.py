#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Prerequisites:
# - Local: bazel and rsync must be in PATH
# - Remote: python3 must be available
# - install: 'deploy' user needs passwordless sudo for useradd, chown, chmod, tee, and systemctl
# - install: /etc/cmk-werk-ids/secret must exist on the remote before running
# - deploy: 'deploy' user needs passwordless sudo for systemctl

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

_REMOTE = "deploy@werk-ids.lan.checkmk.net"
_SERVICE_NAME = "cmk-werk-ids"
_WHEEL_DIR = "/opt/cmk-werk-ids/wheels"
_VENV = "/opt/cmk-werk-ids/venv"
_SECRET_FILE = "/etc/cmk-werk-ids/secret"
_SOCKET_FILE = f"/etc/systemd/system/{_SERVICE_NAME}.socket"
_SERVICE_FILE = f"/etc/systemd/system/{_SERVICE_NAME}.service"
_SOCKET_PATH = f"/run/{_SERVICE_NAME}/gunicorn.sock"

_SOCKET_UNIT = f"""\
[Unit]
Description=Checkmk werk IDs socket

[Socket]
ListenStream={_SOCKET_PATH}
SocketUser={_SERVICE_NAME}
SocketGroup={_SERVICE_NAME}
SocketMode=0660

[Install]
WantedBy=sockets.target
"""

_SERVICE_UNIT = f"""\
[Unit]
Description=Checkmk werk IDs server
Requires={_SERVICE_NAME}.socket
After={_SERVICE_NAME}.socket

[Service]
Type=notify
NotifyAccess=main
User={_SERVICE_NAME}
Group={_SERVICE_NAME}
StateDirectory={_SERVICE_NAME}
ConfigurationDirectory={_SERVICE_NAME}
RuntimeDirectory={_SERVICE_NAME}
ExecStart={_VENV}/bin/python -m cmk.werk_ids_server serve
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""


class Runner:
    def __init__(self, *, dry_run: bool) -> None:
        self.dry_run = dry_run

    def ssh(self, remote: str, cmd: str, *, stdin: str | None = None) -> None:
        if self.dry_run:
            sys.stderr.write(f"[dry-run] ssh {remote} {cmd!r}\n")
            return
        subprocess.run(["ssh", remote, cmd], check=True, input=stdin, text=stdin is not None)

    def local(self, cmd: Sequence[str]) -> None:
        if self.dry_run:
            sys.stderr.write(f"[dry-run] {' '.join(cmd)}\n")
            return
        subprocess.run(cmd, check=True)


def _build_wheel(runner: Runner) -> Path:
    sys.stderr.write("--- Building wheel\n")
    if runner.dry_run:
        return Path("cmk_werk_ids_server-1.0.0-py3-none-any.whl")
    runner.local(["bazel", "build", "//packages/cmk-werks:wheel_server"])
    result = subprocess.run(
        ["bazel", "cquery", "--output=files", "//packages/cmk-werks:wheel_server"],
        check=True,
        capture_output=True,
        text=True,
    )
    wheel_rel = next(p for p in result.stdout.splitlines() if p.endswith(".whl"))
    return Path(wheel_rel).resolve()


def _sync_wheel(remote: str, wheel: Path, runner: Runner) -> None:
    sys.stderr.write(f"--- Syncing wheel to {remote}:{_WHEEL_DIR}\n")
    runner.ssh(remote, f"mkdir -p '{_WHEEL_DIR}'")
    runner.local(["rsync", "-az", "--delete", str(wheel), f"{remote}:{_WHEEL_DIR}/"])


def _pip_install(remote: str, wheel: Path, runner: Runner) -> None:
    runner.ssh(
        remote,
        f"set -euo pipefail; "
        f"'{_VENV}/bin/pip' install --quiet --upgrade pip; "
        f"'{_VENV}/bin/pip' install --quiet --upgrade '{_WHEEL_DIR}/{wheel.name}'",
    )


def _install(remote: str, runner: Runner) -> None:
    sys.stderr.write("--- Checking secret on remote\n")
    runner.ssh(
        remote,
        f"test -f '{_SECRET_FILE}' || "
        f"{{ echo 'ERROR: {_SECRET_FILE} does not exist.' >&2; exit 1; }}",
    )

    wheel = _build_wheel(runner)
    _sync_wheel(remote, wheel, runner)

    sys.stderr.write(f"--- Creating system user {_SERVICE_NAME}\n")
    runner.ssh(
        remote,
        f"id -u '{_SERVICE_NAME}' &>/dev/null || "
        f"sudo useradd --system --no-create-home --shell /usr/sbin/nologin '{_SERVICE_NAME}'; "
        f"sudo chown '{_SERVICE_NAME}:{_SERVICE_NAME}' '{_SECRET_FILE}'; "
        f"sudo chmod 640 '{_SECRET_FILE}'",
    )

    sys.stderr.write(f"--- Installing package into {_VENV}\n")
    runner.ssh(remote, f"mkdir -p '{Path(_VENV).parent}'; python3 -m venv '{_VENV}'")
    _pip_install(remote, wheel, runner)

    sys.stderr.write("--- Installing systemd socket and service\n")
    runner.ssh(remote, f"sudo tee '{_SOCKET_FILE}' > /dev/null", stdin=_SOCKET_UNIT)
    runner.ssh(remote, f"sudo tee '{_SERVICE_FILE}' > /dev/null", stdin=_SERVICE_UNIT)
    runner.ssh(
        remote,
        f"sudo systemctl daemon-reload; "
        f"sudo systemctl enable --now '{_SERVICE_NAME}.socket'; "
        f"sudo systemctl enable '{_SERVICE_NAME}'",
    )

    sys.stderr.write(
        f"Install complete. Run 'systemctl status {_SERVICE_NAME}' on {remote} to verify.\n"
    )


def _deploy(remote: str, runner: Runner) -> None:
    wheel = _build_wheel(runner)
    _sync_wheel(remote, wheel, runner)

    sys.stderr.write("--- Reinstalling package on remote\n")
    _pip_install(remote, wheel, runner)
    runner.ssh(remote, f"sudo systemctl restart {_SERVICE_NAME}")

    sys.stderr.write("--- Deploy complete\n")
    runner.ssh(remote, f"systemctl status {_SERVICE_NAME} --no-pager")


def main() -> None:
    remote_arg = argparse.ArgumentParser(add_help=False)
    remote_arg.add_argument(
        "remote",
        nargs="?",
        default=_REMOTE,
        metavar="user@host",
        help=f"target server (default: {_REMOTE})",
    )

    parser = argparse.ArgumentParser(description="Manage the werk IDs server")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print commands without executing them",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("install", parents=[remote_arg], help="First-time installation")
    sub.add_parser("deploy", parents=[remote_arg], help="Update an existing installation")

    args = parser.parse_args()
    runner = Runner(dry_run=args.dry_run)

    if args.command == "install":
        _install(args.remote, runner)
    elif args.command == "deploy":
        _deploy(args.remote, runner)
    else:
        raise AssertionError(f"Unexpected command: {args.command!r}")


if __name__ == "__main__":
    main()
