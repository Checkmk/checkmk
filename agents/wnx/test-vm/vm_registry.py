# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The test VMs core-vm runs, for winvm (README.md, "Working with running test
VMs").

Each VM has a directory ROOT/<id> (vm1, vm2, ...: the lowest free one) with
vm.json, which names its core-vm process (pid and start time, so that a
reused pid is not taken for it), the worktree it was started in,
when, the sockets of its guest agent and serial console and the token of
the `winvm start --headless` that started it, if one did, and the lock
file that serialises the commands to its guest agent, which serves one
client at a time. ROOT is $XDG_RUNTIME_DIR/qemu-windows, or a directory of
this user's in /tmp. An entry whose core-vm is gone is dropped by the next
listing. Dropping renames the directory out of the way first, and only
while its vm.json still names the process that is gone: its ID may have
been taken again meanwhile.
"""

import contextlib
import fcntl
import json
import os
import secrets
import shutil
import signal
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# The variable through which `winvm start --headless` hands core-vm the token
# that tells it its VM from others.
START_TOKEN = "WINVM_START_TOKEN"

# How long a directory may lack its vm.json: core-vm writes it right after
# creating the directory.
_REGISTERING = 60.0

# The prefix of an entry directory on its way out, not one of the vm* IDs.
_DROPPED = "dropped-"


class RegistryError(Exception):
    pass


@dataclass(frozen=True)
class Vm:
    id: str
    dir: Path
    pid: int
    # The process's start time in clock ticks since boot (/proc/PID/stat).
    pid_start: int
    worktree: str
    started: float
    qga: Path
    console: Path
    # START_TOKEN of the core-vm, empty if it was started otherwise.
    token: str = ""


def default_root() -> Path:
    if runtime := os.environ.get("XDG_RUNTIME_DIR"):
        return Path(runtime, "qemu-windows")
    return Path(tempfile.gettempdir(), f"qemu-windows-{os.getuid()}")


class Registry:
    def __init__(self, root: Path) -> None:
        self.root = root

    @contextlib.contextmanager
    def register(self, qga: Path, console: Path, worktree: str, token: str = "") -> Iterator[Vm]:
        """This process's VM, under the lowest free ID, until the end of
        the block."""
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Frees the IDs of VMs that are gone.
        self.vms()
        number = 1
        while True:
            directory = self.root / f"vm{number}"
            try:
                directory.mkdir()
                break
            except FileExistsError:
                number += 1
        pid = os.getpid()
        vm = Vm(
            directory.name,
            directory,
            pid,
            _start(pid) or 0,
            worktree,
            time.time(),
            qga,
            console,
            token,
        )
        try:
            entry = directory / "vm.json.tmp"
            entry.write_text(
                json.dumps(
                    {
                        "pid": vm.pid,
                        "pid_start": vm.pid_start,
                        "worktree": vm.worktree,
                        "started": vm.started,
                        "qga": str(vm.qga),
                        "console": str(vm.console),
                        "token": vm.token,
                    }
                )
            )
            entry.rename(directory / "vm.json")
            yield vm
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def vms(self) -> list[Vm]:
        """The running VMs, by ID."""
        if not self.root.exists():
            return []
        # In /tmp another user could have made it, and so its entries.
        if self.root.stat().st_uid != os.getuid():
            raise RegistryError(f"{self.root} belongs to another user")
        # Left over by a drop that was cut short.
        for dropped in self.root.glob(f"{_DROPPED}*"):
            shutil.rmtree(dropped, ignore_errors=True)
        found = []
        for directory in sorted(self.root.glob("vm*"), key=_number):
            try:
                data = json.loads((directory / "vm.json").read_text())
            except FileNotFoundError:
                if _age(directory) > _REGISTERING:
                    _drop(directory, None)
                continue
            if _start(data["pid"]) != data["pid_start"]:
                _drop(directory, (data["pid"], data["pid_start"]))
                continue
            found.append(
                Vm(
                    directory.name,
                    directory,
                    data["pid"],
                    data["pid_start"],
                    data["worktree"],
                    data["started"],
                    Path(data["qga"]),
                    Path(data["console"]),
                    data.get("token", ""),
                )
            )
        return found

    def find(self, vm_id: str | None) -> Vm:
        """The VM vm_id, or the only one running."""
        vms = self.vms()
        if vm_id is not None:
            for vm in vms:
                if vm.id == vm_id:
                    return vm
            raise RegistryError(f"no test VM {vm_id} is running{_running(vms)}")
        if len(vms) == 1:
            return vms[0]
        if not vms:
            raise RegistryError("no test VM is running: start one with `winvm start --headless`")
        raise RegistryError(f"several test VMs are running, pick one with --vm{_running(vms)}")


def stop(vm: Vm, timeout: float = 60.0) -> None:
    """Ends vm's core-vm, which quits the VM and drops its entry, and waits
    for both."""
    if _start(vm.pid) == vm.pid_start:
        os.kill(vm.pid, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    while _start(vm.pid) == vm.pid_start:
        if time.monotonic() >= deadline:
            raise RegistryError(f"{vm.id}: core-vm (pid {vm.pid}) still runs after {timeout:g} s")
        time.sleep(0.2)
    # Gone without cleaning up, e.g. killed.
    _drop(vm.dir, (vm.pid, vm.pid_start))


@contextlib.contextmanager
def locked(vm: Vm, *, wait: bool = True) -> Iterator[None]:
    """The VM's guest agent for this process alone; without wait, a VM
    that another command holds fails at once."""
    with (vm.dir / "lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except BlockingIOError:
            raise RegistryError(f"{vm.id} is busy with another winvm command") from None
        yield


def _drop(directory: Path, process: tuple[int, int] | None) -> None:
    """Removes the entry directory if its vm.json still names process
    (pid and start time), or if it still has none for process None."""
    try:
        data = json.loads((directory / "vm.json").read_text())
        current = (data["pid"], data["pid_start"])
    except FileNotFoundError:
        current = None
    except OSError, ValueError, KeyError:
        return
    if current != process:
        return
    claimed = directory.with_name(f"{_DROPPED}{secrets.token_hex(8)}")
    try:
        directory.rename(claimed)
    except OSError:
        # Dropped by another process meanwhile.
        return
    shutil.rmtree(claimed, ignore_errors=True)


def _running(vms: list[Vm]) -> str:
    return "".join(f"\n  {vm.id}  {vm.worktree}" for vm in vms) if vms else ""


def _number(directory: Path) -> int:
    digits = directory.name.removeprefix("vm")
    return int(digits) if digits.isdigit() else 0


def _age(directory: Path) -> float:
    try:
        return time.time() - directory.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def _start(pid: int) -> int | None:
    """When process pid started, None if there is none."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    # Fields 3 on; the command name in field 2 may hold spaces and parentheses.
    fields = stat.rpartition(")")[2].split()
    # A zombie has ended, only its parent has not collected it yet.
    return None if fields[0] == "Z" else int(fields[19])
