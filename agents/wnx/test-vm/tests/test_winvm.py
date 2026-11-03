# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# What the guest's cmd.exe and PowerShell make of winvm's commands is
# vm_smoke's part (tests/vm).

import contextlib
import io
import os
import subprocess
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import override
from unittest.mock import Mock

import pytest
from qemu_windows.guest import Guest, GuestError
from qemu_windows.qga import Qga
from vm_registry import default_root, locked, Registry, stop, Vm
from winvm import (
    complete,
    connect_at_once,
    find_checkout,
    get_paths,
    guest_path,
    main,
    put_target,
    start_headless,
    StartError,
    UsageError,
)

# A `bazel` that, for `bazel run ... core-vm -- --no-shell`, logs as Bazel
# does before it runs core-vm, then registers a VM as core-vm does and holds
# it until SIGTERM.
BAZEL_STARTING_A_VM = """
import os, signal, sys, time
from pathlib import Path
from vm_registry import default_root, Registry, START_TOKEN
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
print("INFO: Running command line: bazel-bin/agents/wnx/test-vm/core-vm", flush=True)
with Registry(default_root()).register(
    Path("qga"), Path("console"), os.getcwd(), os.environ[START_TOKEN]
):
    time.sleep(600)
"""
# A `bazel` whose core-vm runs but never gets its VM going.
BAZEL_WITH_A_STUCK_CORE_VM = """
import signal, sys, time
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
print("INFO: Running command line: bazel-bin/agents/wnx/test-vm/core-vm", flush=True)
time.sleep(600)
"""
BAZEL_FAILING = """
import sys
print("ERROR: no such target '//agents/wnx/test-vm:core-vm'")
sys.exit(1)
"""


@dataclass(frozen=True)
class FakeGuest(Guest):
    """A guest whose PowerShell exits with exit_code and leaves no output,
    and whose cmd.exe prints nothing."""

    exit_code: int = 0

    @override
    def run(
        self, argv: Sequence[str], *, check: bool = True, timeout: float = 3600.0
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, "", "")

    @override
    def powershell(
        self, script: str, *, check: bool = True, timeout: float = 3600.0
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(script, self.exit_code, "", "")

    @override
    def read(self, remote: str) -> bytes:
        raise GuestError(f"guest-file-open: {remote}: not found")


@dataclass
class Vms:
    registry: Registry
    guest: FakeGuest
    connections: list[str] = field(default_factory=list)

    @contextlib.contextmanager
    def connect(self, vm: Vm) -> Iterator[Guest]:
        self.connections.append(vm.id)
        yield self.guest


@pytest.fixture(name="vms")
def fixture_vms(tmp_path: Path) -> Iterator[Vms]:
    """One running VM."""
    registry = Registry(tmp_path / "registry")
    with registry.register(Path("qga"), Path("console"), "worktree"):
        yield Vms(registry, FakeGuest(Mock(spec=Qga), lambda: None, exit_code=3))


@pytest.fixture(name="checkout")
def fixture_checkout(tmp_path: Path) -> Path:
    checkout = tmp_path / "check_mk"
    (checkout / "agents/wnx/test-vm").mkdir(parents=True)
    (checkout / "MODULE.bazel").touch()
    (checkout / "agents/wnx/test-vm/BUILD.bazel").touch()
    return checkout


def with_bazel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script: str) -> Registry:
    """script as the `bazel` on PATH, and the registry it and winvm use."""
    (bin_dir := tmp_path / "bin").mkdir()
    (bazel := bin_dir / "bazel").write_text(f"#!{sys.executable}\n{script}")
    bazel.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(sys.path))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))
    return Registry(default_root())


def test_checkout_is_found_above_a_modules_own_module_file(checkout: Path) -> None:
    module = checkout / "bazel/registry/modules/foo"
    module.mkdir(parents=True)
    (module / "MODULE.bazel").touch()
    assert find_checkout(module) == checkout


def test_start_outside_a_checkout_says_so(tmp_path: Path) -> None:
    with pytest.raises(StartError, match="inside a check_mk checkout"):
        find_checkout(tmp_path)


def test_headless_start_prints_the_id_of_the_vm_it_started(
    checkout: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = with_bazel(tmp_path, monkeypatch, BAZEL_STARTING_A_VM)
    out = io.StringIO()
    with registry.register(Path("qga"), Path("console"), "already running"):
        try:
            assert main(["start", "--headless"], out=out, cwd=checkout) == 0
        finally:
            for vm in registry.vms():
                if vm.worktree != "already running":
                    stop(vm, timeout=10)
    assert out.getvalue() == "vm2\n"


def test_headless_start_gives_up_on_a_core_vm_without_a_vm(
    checkout: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = with_bazel(tmp_path, monkeypatch, BAZEL_WITH_A_STUCK_CORE_VM)
    with pytest.raises(StartError, match="core-vm ran 1 s without its VM"):
        start_headless(checkout, registry, timeout=1, err=io.StringIO())


def test_headless_start_that_fails_shows_core_vms_output(
    checkout: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with_bazel(tmp_path, monkeypatch, BAZEL_FAILING)
    assert main(["start", "--headless"], cwd=checkout) == 1
    assert "ERROR: no such target" in capsys.readouterr().err


def test_guest_path_takes_slashes_as_separators() -> None:
    assert guest_path("C:/Program Files/x.log") == "C:\\Program Files\\x.log"


def test_guest_path_without_drive_is_refused() -> None:
    with pytest.raises(UsageError, match="give guest paths with their drive"):
        guest_path("/")


def test_put_without_remote_copies_into_c() -> None:
    assert put_target("stuff.txt", None, lambda _path: False) == "C:\\stuff.txt"


def test_put_into_a_path_ending_in_a_separator_keeps_the_name() -> None:
    assert put_target("stuff.txt", "C:/data/", lambda _path: False) == "C:\\data\\stuff.txt"


def test_put_into_an_existing_guest_directory_keeps_the_name() -> None:
    assert put_target("stuff.txt", "C:/data", lambda path: path == "C:\\data") == (
        "C:\\data\\stuff.txt"
    )


def test_put_to_a_file_path_takes_that_name() -> None:
    assert put_target("stuff.txt", "C:/data/copy.txt", lambda _path: False) == (
        "C:\\data\\copy.txt"
    )


def test_get_without_local_copies_into_the_working_directory(tmp_path: Path) -> None:
    assert get_paths("C:/logs/agent.log", None, tmp_path) == (
        "C:\\logs\\agent.log",
        tmp_path / "agent.log",
    )


def test_get_into_a_local_directory_keeps_the_name(tmp_path: Path) -> None:
    (tmp_path / "logs").mkdir()
    assert get_paths("C:\\agent.log", "logs", tmp_path)[1] == tmp_path / "logs/agent.log"


def test_get_into_a_path_ending_in_a_slash_keeps_the_name(tmp_path: Path) -> None:
    assert get_paths("C:\\agent.log", "new/", tmp_path)[1] == tmp_path / "new/agent.log"


def test_get_of_a_directory_is_refused(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="not a file"):
        get_paths("C:/logs/", None, tmp_path)


def test_exec_exits_with_the_scripts_exit_code(vms: Vms) -> None:
    out = io.StringIO()
    assert (
        main(["exec", "--", "exit", "3"], registry=vms.registry, connect=vms.connect, out=out) == 3
    )


def test_exec_on_a_vm_that_is_not_running_says_so(
    vms: Vms, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["exec", "--vm", "vm2", "--", "exit"], registry=vms.registry, connect=vms.connect)
    error = capsys.readouterr().err.splitlines()[0]
    assert (code, error) == (1, "error: no test VM vm2 is running")


def test_completes_subcommands(vms: Vms) -> None:
    assert complete(["s"], vms.registry, vms.connect) == ["start", "stop"]


def test_completes_the_options_of_the_subcommand(vms: Vms) -> None:
    assert complete(["start", "-"], vms.registry, vms.connect) == ["--headless"]


def test_completes_vm_ids(vms: Vms) -> None:
    assert complete(["put", "--vm", ""], vms.registry, vms.connect) == ["vm1"]


def test_guest_path_completion_reuses_a_fresh_listing(vms: Vms) -> None:
    complete(["get", "C:/P"], vms.registry, vms.connect)
    complete(["get", "C:/Pr"], vms.registry, vms.connect)
    assert vms.connections == ["vm1"]


def test_guest_path_completion_skips_a_vm_busy_with_another_command(vms: Vms) -> None:
    (vm,) = vms.registry.vms()
    with locked(vm):
        assert not complete(["get", "C:/P"], vms.registry, connect_at_once)
