#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The action behind windows_vm_state(): boots the published,
cleanly shut down test image once, lets it settle and saves the running VM,
so that every test resumes it in seconds instead of booting
(qemu_windows/state.py).

Outputs: a qcow2 overlay on top of the image with the disk writes of that
boot (its backing file recorded by basename only: every user passes the
backing node explicitly), and the VM's RAM and device state as
`migrate file:` writes it. Both are only valid for this image, this QEMU
build, this device set (machine.py) and this host CPU (-cpu host), which is
why the CPU fingerprint is an input.

The VM is saved with PowerShell logged in on its serial console
(qemu_windows/console.py), which core-vm switches to.
"""

import argparse
import contextlib
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

from qemu_windows import console, host_cpu, machine, process
from qemu_windows.errors import VmError
from qemu_windows.guest import Guest, ps_quote
from qemu_windows.qemu import Qemu
from qemu_windows.qga import Qga

_GUEST_DIR = r"C:\Windows\Temp"
# Seconds for the guest to zero what its last processes freed: a few MB.
_SETTLE = 3


def main(argv: Sequence[str] | None = None) -> int:
    # A cancelled action's SIGTERM ends the VM like Ctrl-C.
    process.setup()
    parser = argparse.ArgumentParser(description="Saves a running Windows test VM.")
    for tool in (
        *("qemu", "qemu-img", "bios", "image", "fingerprint"),
        *("warm-up", "wait-idle", "purge-standby"),
    ):
        parser.add_argument(f"--{tool}", type=Path, required=True)
    parser.add_argument("--cpus", type=int, required=True)
    parser.add_argument("--memory-mib", type=int, required=True)
    parser.add_argument("--disk", type=Path, required=True, help="the disk overlay it writes")
    parser.add_argument("--state", type=Path, required=True, help="the VM state it writes")
    args = parser.parse_args(argv)
    try:
        # KVM first, for its hint on a missing or inaccessible /dev/kvm. The
        # fingerprint is this output's cache key: it must describe this host.
        machine.check_kvm()
        host_cpu.check_host(args.qemu, args.fingerprint)
        work = Path(tempfile.mkdtemp(prefix="windows-vm-state."))
        try:
            _save(args, work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    except (VmError, subprocess.CalledProcessError) as e:
        sys.stderr.write(f"error: {e}\n")
        return 1
    return 0


def _save(args: argparse.Namespace, work: Path) -> None:
    start = time.monotonic()

    def step(message: str) -> None:
        sys.stdout.write(f"[{time.monotonic() - start:.0f} s] {message}\n")

    image = args.image.resolve()
    disk = args.disk.absolute()
    state = args.state.absolute()
    machine.overlay(args.qemu_img, image, disk)
    argv = machine.argv(
        args.qemu.resolve(),
        args.bios.resolve().parent,
        machine.Size(args.cpus, args.memory_mib),
        [machine.Disk("image", image, mode="ro"), machine.Disk("state", disk, "image")],
    )
    with Qemu.start(argv, work) as vm:
        step("booting")
        with contextlib.closing(Qga(vm.qga_socket, vm.alive)) as agent:
            guest = Guest(agent, vm.check)
            guest.wait_ready(900)
            guest.wait_console(600)
            guest.set_clock()
            step("logged on")
            # Before waiting for idle, which then covers PowerShell's start.
            _log_in_on_console(vm.console_socket)
            step("PowerShell on the serial console")
            # Work that Windows does on first use, done here once instead
            # of in every test; waiting for idle then covers it too.
            warm_up = _run_script(guest, args.warm_up)
            sys.stdout.write(warm_up.stdout)
            if warm_up.returncode:
                raise VmError(f"warming up the guest failed:\n{warm_up.stderr}")
            step("warmed up")
            # Saving a guest that is still busy (post-logon indexing,
            # licensing, .NET) would replay that work at the start of every
            # test. Generous: under host load CI takes longer to settle, but
            # a guest that never does is a bug.
            idle = _run_script(guest, args.wait_idle, "-TimeoutSec", "900")
            sys.stdout.write(idle.stdout)
            if idle.returncode:
                raise VmError(f"the guest did not go idle:\n{idle.stderr}")
            step("idle")
            # The file cache would be saved with the RAM: empty it.
            purge = _run_script(guest, args.purge_standby)
            sys.stdout.write(purge.stdout)
            if purge.returncode:
                sys.stdout.write(
                    "warning: purging the guest file cache failed; the state is larger\n"
                )
        # The guest agent's port is saved without a client: every resume
        # connects anew. purge-standby.ps1 waited for the zero-page thread;
        # this is for the pages of the last guest processes, which have
        # ended since.
        time.sleep(_SETTLE)
        # Stopped first: a live migration into a file appends every page the
        # guest dirties meanwhile. Completion flushes and inactivates the
        # disks, so the overlay is consistent once QEMU quits.
        vm.qmp("stop")
        state.unlink(missing_ok=True)
        vm.qmp("migrate", {"uri": f"file:{state}"})
        vm.wait_migration(300)
        vm.quit()
    # The overlay alone, without the image it names.
    overlay = {
        "driver": "qcow2",
        "file": {"driver": "file", "filename": str(disk)},
        "backing": None,
    }
    subprocess.run([args.qemu_img, "check", "-q", f"json:{json.dumps(overlay)}"], check=True)
    step(
        f"saved: disk overlay {disk.stat().st_size >> 20} MiB, state {state.stat().st_size >> 20} MiB"
    )


def _log_in_on_console(path: Path) -> None:
    """A PowerShell session on the serial console, in console.SESSION. SAC
    takes its cmd only once its service runs, a minute or so after boot."""
    with socket.socket(socket.AF_UNIX) as sock:
        sock.connect(str(path))
        channel = console.login(sock, timeout=600)
    if channel != console.SESSION:
        raise VmError(
            f"PowerShell on the serial console is in {channel.decode()},"
            f" not in {console.SESSION.decode()}"
        )


def _run_script(guest: Guest, script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """A guest-side PowerShell script, run as LocalSystem; removed afterwards."""
    remote = rf"{_GUEST_DIR}\{script.name}"
    guest.put(script, remote)
    try:
        return guest.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass"]
            + ["-File", remote, *arguments],
            check=False,
            timeout=1200,
        )
    finally:
        guest.powershell(f"Remove-Item -LiteralPath {ps_quote(remote)}", check=False)


if __name__ == "__main__":
    sys.exit(main())
