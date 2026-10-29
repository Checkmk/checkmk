# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Resuming a saved test VM (windows_vm_state.bzl, save_state.py).

A saved state is a disk overlay on top of the image plus the RAM and device
state that `migrate file:` wrote. It only resumes on the device set and
size (machine.argv), the QEMU build and the host CPU it was saved with.
"""

import contextlib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Self

from qemu_windows import host_cpu, machine
from qemu_windows.errors import VmError
from qemu_windows.guest import Guest
from qemu_windows.qemu import Qemu
from qemu_windows.qga import Qga


@dataclass(frozen=True)
class SavedVm:
    """What it takes to resume a saved test VM."""

    qemu: Path
    qemu_img: Path
    # The directory -L wants.
    firmware: Path
    image: Path
    disk: Path
    state: Path
    # The size the state was saved with.
    size: machine.Size

    @classmethod
    def of(
        cls,
        *,
        qemu: Path,
        qemu_img: Path,
        bios: Path,
        image: Path,
        disk: Path,
        state: Path,
        size: machine.Size,
    ) -> Self:
        """From the paths Bazel hands over, resolved."""
        return cls(
            qemu=qemu.resolve(),
            qemu_img=qemu_img.resolve(),
            # A file in the firmware directory -L wants.
            firmware=bios.resolve().parent,
            image=image.resolve(),
            disk=disk.resolve(),
            state=state.resolve(),
            size=size,
        )


def check(saved: SavedVm, fingerprint: Path, expires: date) -> None:
    """Fails unless saved can resume on this host: KVM is usable, the
    image's Eval licence (ending at expires) is still good and the host CPU
    matches the fingerprint the state was saved for."""
    check_expiry(expires, date.today())
    machine.check_kvm()
    # The state matches the fingerprint, not necessarily this host: on a
    # stale fingerprint it was saved on another CPU and would not resume.
    host_cpu.check_host(saved.qemu, fingerprint)


def check_expiry(expires: date, today: date) -> None:
    """Fails from the day before the image's Eval licence expires: an expired
    licence shuts the guest down every hour."""
    if today >= expires - timedelta(days=1):
        raise VmError(
            f"the Windows test image's Eval licence expires {expires}:"
            " build and pin a new image (agents/wnx/test-vm)."
        )


@contextlib.contextmanager
def resume(saved: SavedVm, workdir: Path) -> Iterator[tuple[Qemu, Guest]]:
    """The saved VM, running again on a throwaway disk layer of its own in
    workdir: image (read-only) <- the state's disk (read-only, shared) <-
    workdir/disk.qcow2. Ready once the guest agent answers, with the guest
    clock set from the host's (the state may be days old). The VM ends
    with the context."""
    workdir.mkdir(parents=True, exist_ok=True)
    disk = workdir / "disk.qcow2"
    machine.overlay(saved.qemu_img, saved.disk, disk)
    argv = machine.argv(
        saved.qemu,
        saved.firmware,
        saved.size,
        [
            machine.Disk("image", saved.image, mode="ro"),
            machine.Disk("state", saved.disk, "image", "ro"),
            machine.Disk("test", disk, "state", "scratch"),
        ],
    )
    with Qemu.start(argv, workdir, ["-incoming", f"file:{saved.state}"]) as vm:
        # A restore takes seconds.
        vm.wait_migration(60)
        vm.qmp("cont")
        # The restore brings back the link state the NIC had when saved.
        vm.qmp("set_link", {"name": "nic1", "up": False})
        with contextlib.closing(Qga(vm.qga_socket, vm.alive)) as agent:
            guest = Guest(agent, vm.check)
            guest.wait_ready(60)
            guest.set_clock()
            yield vm, guest


@contextlib.contextmanager
def resume_from_env(env: Mapping[str, str], workdir: Path) -> Iterator[tuple[Qemu, Guest]]:
    """check() and resume() for the saved VM that the QEMU_WINDOWS_*
    variables of a test describe (test_vm_env() in
    agents/wnx/test-vm/image.bzl)."""
    saved = SavedVm.of(
        qemu=Path(env["QEMU_WINDOWS_QEMU"]),
        qemu_img=Path(env["QEMU_WINDOWS_QEMU_IMG"]),
        bios=Path(env["QEMU_WINDOWS_FIRMWARE"]),
        image=Path(env["QEMU_WINDOWS_IMAGE"]),
        disk=Path(env["QEMU_WINDOWS_STATE_DISK"]),
        state=Path(env["QEMU_WINDOWS_STATE"]),
        size=machine.Size(int(env["QEMU_WINDOWS_CPUS"]), int(env["QEMU_WINDOWS_MEMORY_MIB"])),
    )
    check(
        saved,
        Path(env["QEMU_WINDOWS_CPU_FINGERPRINT"]),
        date.fromisoformat(env["QEMU_WINDOWS_EXPIRES"]),
    )
    with resume(saved, workdir) as (vm, guest):
        yield vm, guest
