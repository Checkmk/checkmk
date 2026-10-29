# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Runs a *-qemu test tier's payload in a Windows test VM.

A tier's runner (qemu_test, bazel/rules/xcomp/qemu_test.bzl) stages what its
payload needs into a Stage, with a task.cmd, and ends with run(), which
copies the stage into the guest as C:\\bzl-NAME-<pid>-<time> and runs task.cmd
there in the guest's autologon console session, as the Administrator with
the elevated token (session.run_in_session): run-as spawns and COM services
such as Windows Update need that session, and the guest agent itself runs as
LocalSystem in session 0.

task.cmd runs in that directory, with its path in QEMU_GDIR and its name,
unique per run, in QEMU_RID. Its exit code (ERRORLEVEL at its end, or exit /b
N) is the result: 0 passes, anything else fails, including the NTSTATUS of a
crash. It must not call plain `exit`, which would end the wrapper that
records the result. Its output is printed once it has finished. The stage is
deleted once it is in the guest: task.cmd can hold credentials.

Every test gets its own VM: the saved state of the Server Core test image
(windows_vm_state.bzl), resumed on a throwaway disk layer in TEST_TMPDIR
(state.resume_from_env), which ends with the test, and with it everything
the payload left in the guest.

Environment:
  QEMU_WINDOWS_*      set by qemu_test(): the QEMU build, the image, its
                      saved state, the host CPU fingerprint that state is
                      keyed on, the VM's size and the image's Eval expiry
  TEST_TIMEOUT        set by Bazel: the test's timeout in seconds (the
                      target's timeout, or --test_timeout). task.cmd gets
                      what the VM's start and the staging leave of it, less
                      TEARDOWN.
"""

import contextlib
import os
import shutil
import sys
import tarfile
import time
from collections.abc import Sequence
from pathlib import Path

from qemu_windows import process, state
from qemu_windows.errors import VmError
from qemu_windows.guest import Guest, ps_quote
from qemu_windows.session import run_in_session, SessionError
from qemu_windows.stage import Stage

# Bazel's timeout counts from the test's start, about when the runner
# imports this module.
_STARTED = time.monotonic()

# What run() keeps of Bazel's timeout after task.cmd's share: to end a
# task.cmd that ran out of time, print its output so far and end the VM,
# before Bazel's SIGTERM.
TEARDOWN = 60.0


def run(
    name: str,
    stage: Stage,
    *,
    collect: Sequence[str] = (),
) -> int:
    """Runs the stage's task.cmd in the guest: the test's exit code.

    collect: files of QEMU_GDIR to copy into the test's undeclared outputs.
    """
    # The payload's output before the verdict that follows it; a Bazel
    # timeout's SIGTERM stops the payload and ends the VM on the way out.
    process.setup()
    rid = f"bzl-{name}-{os.getpid()}-{int(time.time())}"
    try:
        with state.resume_from_env(os.environ, Path(os.environ["TEST_TMPDIR"], "vm")) as (
            _vm,
            guest,
        ):
            return _run(guest, stage.root, rid, collect)
    except VmError as e:
        sys.stderr.write(f"error: {e}\n")
        return 1


def payload_timeout(test_timeout: float, elapsed: float) -> float:
    """Seconds task.cmd gets elapsed s into a test with Bazel's
    test_timeout: the rest, less TEARDOWN."""
    return max(test_timeout - elapsed - TEARDOWN, 0.0)


def _run(
    guest: Guest,
    stage: Path,
    rid: str,
    collect: Sequence[str],
) -> int:
    gdir = rf"C:\{rid}"
    environment = [f"set QEMU_RID={rid}", f"set QEMU_GDIR={gdir}"]
    # The task's working directory and variables. Its exit code is that of
    # the last command, the call.
    Stage(stage).write(
        "qemu-task.cmd",
        "\n".join(["@echo off", *environment, f"cd /d {gdir}", rf"call {gdir}\task.cmd"]),
    )
    try:
        _put_stage(guest, stage, gdir)
        timeout = payload_timeout(
            float(os.environ.get("TEST_TIMEOUT", "900")), time.monotonic() - _STARTED
        )
        try:
            output = run_in_session(guest, rf"{gdir}\qemu-task.cmd", timeout)
        except SessionError as e:
            sys.stdout.write(e.log)
            sys.stderr.write(f"error: task.cmd: {e}\n")
            return 1
        sys.stdout.write(output)
        return 0
    finally:
        _collect(guest, gdir, collect)


def _put_stage(guest: Guest, stage: Path, gdir: str) -> None:
    """The stage into gdir, as one archive: one file to copy is faster than
    many. The stage is gone afterwards, also on the host."""
    archive = stage.with_name(f"{stage.name}.tgz")
    try:
        with tarfile.open(archive, "w:gz", compresslevel=1) as tar:
            tar.add(stage, arcname=".")
        shutil.rmtree(stage)
        guest.powershell(f"New-Item -ItemType Directory -Path {ps_quote(gdir)} | Out-Null")
        guest.put(archive, rf"{gdir}\stage.tgz")
    finally:
        archive.unlink(missing_ok=True)
    guest.run(["tar.exe", "-xzf", rf"{gdir}\stage.tgz", "-C", gdir])
    guest.powershell(f"Remove-Item -LiteralPath {ps_quote(rf'{gdir}\stage.tgz')}")


def _collect(guest: Guest, gdir: str, names: Sequence[str]) -> None:
    """Best effort: a file the payload did not write is no error of its own."""
    if not names or not (outputs := os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")):
        return
    for name in names:
        target = Path(outputs, name)
        with contextlib.suppress(VmError):
            guest.get(rf"{gdir}\{name}", target)
