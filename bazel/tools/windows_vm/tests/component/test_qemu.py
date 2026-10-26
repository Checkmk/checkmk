# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The machine's real device set on the pinned QEMU, without KVM.

accel=qtest instead of kvm, without -cpu host: QEMU builds the whole machine
and serves QMP, but runs no guest code.
"""

import contextlib
import json
import os
import socket
import subprocess
import time
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from qemu_windows.errors import VmError
from qemu_windows.guest import Guest, GuestError
from qemu_windows.machine import argv, Disk, overlay
from qemu_windows.qemu import Qemu
from qemu_windows.qga import Qga
from qemu_windows.qmp import QmpError

QEMU = Path(os.environ["QEMU"])
QEMU_IMG = Path(os.environ["QEMU_IMG"])
FIRMWARE = Path(os.environ["QEMU_BIOS"]).parent


def image(path: Path, size: str = "1G") -> Path:
    subprocess.run([QEMU_IMG, "create", "-q", "-f", "qcow2", path, size], check=True)
    return path


def qtest_argv(disks: Sequence[Disk]) -> list[str]:
    machine = argv(QEMU, FIRMWARE, disks)
    cpu = machine.index("-cpu")
    del machine[cpu : cpu + 2]
    return [arg.replace("accel=kvm", "accel=qtest") for arg in machine]


@pytest.fixture(name="vm")
def fixture_vm(tmp_path: Path) -> Iterator[Qemu]:
    with Qemu.start(
        qtest_argv([Disk("disk", image(tmp_path / "disk.qcow2"))]), tmp_path / "vm"
    ) as vm:
        yield vm


def test_guest_agent_socket_takes_connections_but_no_guest_answers(vm: Qemu) -> None:
    with (
        contextlib.closing(Qga(vm.qga_socket, vm.alive, reply_timeout=0.5)) as agent,
        pytest.raises(GuestError, match="no guest agent within 0 s: .*did not answer"),
    ):
        Guest(agent, vm.check).wait_ready(0)


def test_serial_console_socket_takes_a_connection(vm: Qemu) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as console:
        console.connect(str(vm.console_socket))


def test_started_vm_is_running(vm: Qemu) -> None:
    assert vm.status() == "running"


def test_quit_ends_qemu_cleanly(vm: Qemu) -> None:
    assert vm.quit() == 0


def test_check_fails_once_qemu_has_exited(vm: Qemu) -> None:
    with contextlib.suppress(QmpError):
        vm.qmp("quit")
    deadline = time.monotonic() + 10
    while vm.returncode is None and time.monotonic() < deadline:
        time.sleep(0.05)

    with pytest.raises(VmError, match="QEMU has exited with status 0"):
        vm.check()


def test_start_fails_with_qemus_log_when_qemu_refuses_its_command_line(tmp_path: Path) -> None:
    machine = qtest_argv([Disk("disk", image(tmp_path / "disk.qcow2"))])

    with pytest.raises(VmError, match=r"(?s)QEMU did not start.*no-such-device"):
        Qemu.start(machine, tmp_path / "vm", extra=["-device", "no-such-device"])


def test_migration_to_a_file_completes(vm: Qemu, tmp_path: Path) -> None:
    vm.qmp("stop")
    vm.qmp("migrate", {"uri": f"file:{tmp_path / 'state.bin'}"})

    vm.wait_migration(30)

    assert (tmp_path / "state.bin").stat().st_size > 0


def test_overlay_is_an_empty_layer_of_the_backing_images_size(tmp_path: Path) -> None:
    base = image(tmp_path / "base.qcow2", "3G")

    overlay(QEMU_IMG, base, tmp_path / "top.qcow2")

    info = json.loads(
        subprocess.run(
            [QEMU_IMG, "info", "-U", "--output=json", tmp_path / "top.qcow2"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert (info["virtual-size"], info["backing-filename"]) == (3 * 1024**3, "base.qcow2")
