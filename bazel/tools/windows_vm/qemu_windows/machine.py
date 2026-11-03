# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The QEMU command line of the Windows test VMs.

A saved VM state only resumes on the device set it was saved with, so
everything that makes up the machine lives here, once: machine type (pinned
to the QEMU build), CPU (-cpu host, hence one state per CPU fingerprint), RAM,
the IDE disk, two e1000 NICs, vmgenid, the guest agent's virtio-serial port
and COM1. Callers only choose the disk chain and a few extra devices for the
install boots, which never get saved.
"""

import getpass
import os
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from qemu_windows.errors import VmError

MACHINE = "pc-i440fx-11.1"
# The chardevs of the guest agent's port and of COM1, which Qemu.start adds:
# sockets, whose paths differ per run and are no part of a saved state.
QGA_CHARDEV = "qga"
CONSOLE_CHARDEV = "console"


@dataclass(frozen=True)
class Disk:
    """One qcow2 layer of the disk chain.

    backing names the node below, explicitly: the path recorded in the qcow2
    header (made somewhere else, e.g. in a Bazel action) is never used. "ro"
    is for shared layers, "scratch" for a throwaway top layer that needs no
    flushes.
    """

    node: str
    file: Path
    backing: str | None = None
    mode: Literal["rw", "ro", "scratch"] = "rw"

    def blockdev_args(self) -> list[str]:
        file_opts = f"driver=file,node-name={self.node}-file,filename={self.file}"
        qcow2_opts = f"driver=qcow2,node-name={self.node},file={self.node}-file"
        if self.mode == "ro":
            file_opts += ",read-only=on"
            qcow2_opts += ",read-only=on"
        else:
            # TRIMs and zero writes free qcow2 clusters instead of growing
            # the file.
            file_opts += ",discard=unmap"
            qcow2_opts += ",discard=unmap,detect-zeroes=unmap"
            if self.mode == "scratch":
                file_opts += ",cache.no-flush=on"
        if self.backing is not None:
            qcow2_opts += f",backing={self.backing}"
        return ["-blockdev", file_opts, "-blockdev", qcow2_opts]


@dataclass(frozen=True)
class Size:
    """The guest's vCPUs and RAM (WINDOWS_TEST_VM in agents/wnx/test-vm/image.bzl)."""

    cpus: int
    memory_mib: int


def argv(qemu: Path, firmware: Path, size: Size, disks: Sequence[Disk]) -> list[str]:
    """The machine's QEMU command line; disks bottom first, the guest sees the last."""
    return [
        str(qemu),
        *("-L", str(firmware), "-nodefaults"),
        *("-machine", f"{MACHINE},accel=kvm", "-cpu", "host"),
        *("-m", f"{size.memory_mib}M", "-smp", str(size.cpus)),
        *("-vga", "std", "-display", "none"),
        *(arg for disk in disks for arg in disk.blockdev_args()),
        *("-device", f"ide-hd,drive={disks[-1].node},bus=ide.0,unit=0"),
        # net0 reaches the host as 10.0.2.2 (and the internet). nic1 stays
        # link-down: watest's Wtools.GetAdapterInfoStore needs one adapter
        # in IfOperStatusDown, as on the old CI nodes. Its own subnet keeps
        # Windows from seeing 10.0.2.15 twice.
        *("-netdev", "user,id=net0"),
        *("-device", "e1000,netdev=net0"),
        *("-netdev", "user,id=net1,net=10.0.3.0/24"),
        *("-device", "e1000,netdev=net1,id=nic1"),
        # A new generation ID on every restore: Windows reseeds its RNGs.
        *("-device", "vmgenid,guid=auto"),
        # The guest agent's port (qemu-ga), after the NICs: their PCI slots,
        # and so the guest's adapter names, stay as they were.
        *("-device", "virtio-serial-pci,id=vser0"),
        "-device",
        f"virtserialport,bus=vser0.0,chardev={QGA_CHARDEV},name=org.qemu.guest_agent.0",
        # COM1 for Windows' Special Administration Console (EMS), the way
        # into a guest whose agent does not answer (README.md).
        *("-device", f"isa-serial,chardev={CONSOLE_CHARDEV}"),
    ]


def overlay(qemu_img: Path, backing: Path, new: Path) -> None:
    """An empty qcow2 on top of backing, recorded by basename only and never
    opened (-u): every user passes the backing node explicitly (Disk)."""
    # Not --output=json: that lists the file node's size (the qcow2 file's
    # length) before the image's own.
    info = subprocess.run(
        [qemu_img, "info", backing], check=True, capture_output=True, text=True
    ).stdout
    if not (size := re.search(r"^virtual size: .*\((\d+) bytes\)$", info, re.MULTILINE)):
        raise VmError(f"no virtual size in `qemu-img info {backing}`:\n{info}")
    new.unlink(missing_ok=True)
    subprocess.run(
        [str(qemu_img), "create", "-q", "-f", "qcow2", "-u"]
        + ["-b", backing.name, "-F", "qcow2", str(new), size[1]],
        check=True,
    )


def check_kvm() -> None:
    """Fails unless this process can use KVM, which the machine needs."""
    kvm = Path("/dev/kvm")
    if not kvm.exists():
        raise VmError(
            "/dev/kvm does not exist: this host (or container) has no KVM.\n"
            "In CI the pod needs the devices.kubevirt.io/kvm resource."
        )
    if not os.access(kvm, os.R_OK | os.W_OK):
        raise VmError(
            f"/dev/kvm is not readable and writable for {getpass.getuser()}.\n"
            "Add the user to the kvm group (or log in again after adding it). Bazel took"
            " the host CPU's fingerprint without KVM then: take it anew with"
            " `bazel fetch --force --repo=@qemu_host_cpu`."
        )
