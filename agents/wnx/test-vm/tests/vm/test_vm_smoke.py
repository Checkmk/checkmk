# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""core-vm's shell and winvm against a VM resumed from the saved state, for
what the unit tests can only fake: the guest's cmd.exe and PowerShell, and
SAC on its serial console. Needs KVM and the state:

  bazel test --config=test-vm //agents/wnx/test-vm:vm_smoke
"""

import io
import os
import re
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import winvm
from qemu_windows import state
from qemu_windows.console import attach, SizeQueries
from qemu_windows.qemu import Qemu
from vm_console import relay
from vm_registry import Registry

# The terminal the console session is laid out for.
SIZE = (40, 146)


@pytest.fixture(name="vm", scope="module")
def fixture_vm(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Qemu]:
    with state.resume_from_env(os.environ, tmp_path_factory.mktemp("vm")) as (vm, guest):
        # The guest agent serves one client at a time: winvm's.
        guest.agent.close()
        yield vm


@pytest.fixture(name="registry")
def fixture_registry(vm: Qemu, tmp_path: Path) -> Iterator[Registry]:
    registry = Registry(tmp_path / "registry")
    with registry.register(vm.qga_socket, vm.console_socket, "smoke"):
        yield registry


def winvm_main(registry: Registry, *args: str, cwd: Path | None = None) -> tuple[int, str]:
    out = io.StringIO()
    code = winvm.main(list(args), registry=registry, out=out, cwd=cwd)
    return code, out.getvalue()


def test_exec_shows_the_scripts_output_and_exits_with_its_code(registry: Registry) -> None:
    assert winvm_main(registry, "exec", "--", "'smoke' + 6 * 7; exit 3") == (3, "smoke42\n")


def test_put_into_a_guest_directory_keeps_the_name(registry: Registry, tmp_path: Path) -> None:
    (tmp_path / "smoke.txt").write_text("put by the smoke test")
    winvm_main(registry, "put", "smoke.txt", "C:/Windows/Temp", cwd=tmp_path)
    assert winvm_main(registry, "exec", "Get-Content C:/Windows/Temp/smoke.txt")[1] == (
        "put by the smoke test\n"
    )


def test_get_into_a_local_directory_keeps_the_name(registry: Registry, tmp_path: Path) -> None:
    (tmp_path / "got").mkdir()
    winvm_main(registry, "get", "C:/Windows/win.ini", "got", cwd=tmp_path)
    assert b"[fonts]" in (tmp_path / "got/win.ini").read_bytes()


def test_guest_paths_complete_from_the_guests_listing(registry: Registry) -> None:
    assert "C:/Windows/" in winvm_main(registry, "__complete", "get", "C:/Win")[1].splitlines()


def test_console_session_runs_a_command_and_ends_with_exit(vm: Qemu) -> None:
    """Last: exit ends the VM's only session."""
    stdin_read, stdin_write = os.pipe()
    stdout_read, stdout_write = os.pipe()
    with socket.socket(socket.AF_UNIX) as sock:
        sock.connect(str(vm.console_socket))
        queries = SizeQueries(lambda: SIZE)
        attach(sock, queries)
        relaying = threading.Thread(
            target=relay, args=(sock, stdin_read, stdout_write, queries), daemon=True
        )
        relaying.start()
        os.write(stdin_write, b"'smoke' + 6 * 7\r")
        shown = _read_until(stdout_read, b"smoke42", timeout=30)
        os.write(stdin_write, b"exit\r")
        relaying.join(30)
    # The command ran, and the size answers went to the session, not into
    # its input.
    # A size answer that reached PowerShell as typed text shows without its
    # ESC (SAC drops it); the console host's own ESC[8;40;146t, which sets
    # the terminal to the size it was told, is fine.
    leaked = re.search(rb"(?<!\x1b)\[8;%d;%dt" % SIZE, shown)
    assert (b"smoke42" in shown, leaked, relaying.is_alive()) == (True, None, False), shown
    for fd in (stdin_read, stdin_write, stdout_read, stdout_write):
        os.close(fd)


def _read_until(fd: int, wanted: bytes, timeout: float) -> bytes:
    os.set_blocking(fd, False)
    deadline = time.monotonic() + timeout
    shown = b""
    while wanted not in shown and time.monotonic() < deadline:
        try:
            shown += os.read(fd, 65536)
        except BlockingIOError:
            time.sleep(0.1)
    return shown
