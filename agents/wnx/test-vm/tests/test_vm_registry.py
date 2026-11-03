# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from vm_registry import Registry, RegistryError, stop, Vm

# A process that registers a VM as core-vm does and holds it until SIGTERM.
CORE_VM = """
import signal, sys, time
from pathlib import Path
from vm_registry import Registry

signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
with Registry(Path(sys.argv[1])).register(Path("qga"), Path("console"), "worktree"):
    print("registered", flush=True)
    time.sleep(600)
"""


@contextlib.contextmanager
def core_vm(root: Path) -> Iterator[subprocess.Popen[str]]:
    process = subprocess.Popen(
        [sys.executable, "-c", CORE_VM, str(root)],
        stdout=subprocess.PIPE,
        text=True,
        env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)),
    )
    try:
        assert process.stdout is not None
        assert process.stdout.readline() == "registered\n"
        yield process
    finally:
        process.kill()
        process.wait()


def register(
    registry: Registry, worktree: str = "worktree"
) -> contextlib.AbstractContextManager[Vm]:
    return registry.register(Path("qga"), Path("console"), worktree)


def test_vms_get_the_lowest_free_ids(tmp_path: Path) -> None:
    registry = Registry(tmp_path)
    with register(registry), register(registry):
        assert [vm.id for vm in registry.vms()] == ["vm1", "vm2"]


def test_the_id_of_an_ended_vm_is_free_again(tmp_path: Path) -> None:
    registry = Registry(tmp_path)
    with register(registry):
        with register(registry):
            pass
        with register(registry) as vm:
            assert vm.id == "vm2"


def test_entry_goes_with_its_vm(tmp_path: Path) -> None:
    registry = Registry(tmp_path)
    with register(registry):
        pass
    assert not registry.vms()


def test_entry_of_a_reused_pid_is_dropped(tmp_path: Path) -> None:
    registry = Registry(tmp_path)
    with register(registry) as vm:
        entry = vm.dir / "vm.json"
        data = json.loads(entry.read_text())
        entry.write_text(json.dumps(data | {"pid_start": data["pid_start"] - 1}))

        assert not registry.vms()


def test_find_picks_the_only_vm(tmp_path: Path) -> None:
    registry = Registry(tmp_path)
    with register(registry, "only") as vm:
        assert registry.find(None) == vm


def test_find_needs_an_id_while_several_vms_run(tmp_path: Path) -> None:
    registry = Registry(tmp_path)
    with (
        register(registry),
        register(registry),
        pytest.raises(RegistryError, match="several test VMs are running, pick one with --vm"),
    ):
        registry.find(None)


def test_find_without_a_vm_says_how_to_start_one(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="winvm start --headless"):
        Registry(tmp_path).find(None)


def test_stop_ends_core_vm_which_drops_its_entry(tmp_path: Path) -> None:
    registry = Registry(tmp_path)
    with core_vm(tmp_path) as process:
        (vm,) = registry.vms()

        stop(vm, timeout=10)

        assert process.wait(10) == 0
        assert not vm.dir.exists()


def test_stop_drops_the_entry_of_a_killed_core_vm(tmp_path: Path) -> None:
    registry = Registry(tmp_path)
    with core_vm(tmp_path) as process:
        (vm,) = registry.vms()
        process.kill()
        process.wait()

        stop(vm, timeout=10)

        assert not vm.dir.exists()


def test_stop_leaves_the_entry_of_a_vm_that_took_the_id_meanwhile(tmp_path: Path) -> None:
    registry = Registry(tmp_path)
    with core_vm(tmp_path) as first:
        (stopping,) = registry.vms()
        # It ends and frees vm1, which the next core-vm takes, before stop()
        # gets to look.
        first.terminate()
        first.wait()
        with core_vm(tmp_path) as second:
            stop(stopping, timeout=10)
            assert [(vm.id, vm.pid) for vm in registry.vms()] == [("vm1", second.pid)]
