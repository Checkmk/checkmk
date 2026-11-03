# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Runs a *-qemu test tier's payload in a Windows test VM.

A tier's stage is what its payload needs in the guest: an archive Bazel
builds (qemu_test's stage, bazel/rules/xcomp/qemu_test.bzl). The runner ends
with run(), which extracts it in the guest as C:\\bzl-NAME-<pid>-<time> and
runs the stage's script there in the guest's autologon console session, as
the Administrator with the elevated token (session.run_in_session): run-as
spawns and COM services such as Windows Update need that session, and the
guest agent itself runs as LocalSystem in session 0.

The script, a .cmd or a .ps1 that Windows PowerShell runs, runs in that
directory, with its path in QEMU_GDIR and its name, unique per run, in
QEMU_RID. Its exit code (ERRORLEVEL at its end, exit /b N, or a .ps1's
exit N) is the result: 0 passes, anything else fails, including the
NTSTATUS of a crash. A .cmd must not call plain `exit`, which would end the
wrapper that records the result. Its output is printed once it has
finished.

Every test gets its own VM: the saved state of the Server Core test image
(windows_vm_state.bzl), resumed on a throwaway disk layer in TEST_TMPDIR
(state.resume_from_env), which ends with the test, and with it everything
the payload left in the guest.

Environment:
  QEMU_STAGE          set by qemu_test() with a stage: the runfiles path of
                      the archive Bazel built of it
  QEMU_WINDOWS_*      set by qemu_test(): the QEMU build, the image, its
                      saved state, the host CPU fingerprint that state is
                      keyed on, the VM's size and the image's Eval expiry
  TEST_TIMEOUT        set by Bazel: the test's timeout in seconds (the
                      target's timeout, or --test_timeout). The script gets
                      what the VM's start and the staging leave of it, less
                      TEARDOWN.
"""

import contextlib
import os
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path, PureWindowsPath

from python.runfiles import runfiles
from qemu_windows import process, state
from qemu_windows.errors import VmError
from qemu_windows.guest import Guest, ps_quote
from qemu_windows.session import run_in_session, SessionError

# Bazel's timeout counts from the test's start, about when the runner
# imports this module.
_STARTED = time.monotonic()

# What run() keeps of Bazel's timeout after the script's share: to end a
# script that ran out of time, print its output so far and end the VM,
# before Bazel's SIGTERM.
TEARDOWN = 60.0


def run(
    name: str,
    *,
    script: str,
    args: Sequence[str] = (),
    env: Mapping[str, str] | None = None,
    collect: Sequence[str] = (),
) -> int:
    """Runs the stage's script in the guest: the test's exit code.

    script: the stage path of the .cmd or .ps1 to run, with args.
    args: go into qemu-task.cmd as given: quote one with spaces or & | < >,
      and avoid ^, which call doubles even in quotes; % expands, as in env.
    env: variables to set for it; values can use QEMU_GDIR and QEMU_RID.
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
            return _run(guest, rid, wrapper(rid, script, args, env or {}), collect)
    except VmError as e:
        sys.stderr.write(f"error: {e}\n")
        return 1


def payload_timeout(test_timeout: float, elapsed: float) -> float:
    """Seconds the script gets elapsed s into a test with Bazel's
    test_timeout: the rest, less TEARDOWN."""
    return max(test_timeout - elapsed - TEARDOWN, 0.0)


def read_list(path: Path) -> list[str]:
    """The entries of a list file (test exclusions and the like): one per
    line, surrounding whitespace removed, blank lines and lines starting
    with '#' left out."""
    return [
        entry
        for line in path.read_text().splitlines()
        if (entry := line.strip()) and not entry.startswith("#")
    ]


def wrapper(rid: str, script: str, args: Sequence[str], env: Mapping[str, str]) -> str:
    """qemu-task.cmd, which runs script in C:\\rid with env: its exit code is
    the script's, as that of the wrapper's last command. CRLF line ends, which
    cmd.exe's batch parser needs."""
    gdir = rf"C:\{rid}"
    path = rf"{gdir}\{PureWindowsPath(script)}"
    command = (
        f'powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{path}"'
        if script.endswith(".ps1")
        else f'call "{path}"'
    )
    return "\r\n".join(
        [
            "@echo off",
            f'set "QEMU_RID={rid}"',
            f'set "QEMU_GDIR={gdir}"',
            *(f'set "{name}={value}"' for name, value in env.items()),
            f'cd /d "{gdir}"',
            " ".join([command, *args]),
        ]
    )


def _run(guest: Guest, rid: str, task: str, collect: Sequence[str]) -> int:
    gdir = rf"C:\{rid}"
    try:
        _put_stage(guest, gdir)
        guest.write(rf"{gdir}\qemu-task.cmd", task.encode())
        timeout = payload_timeout(
            float(os.environ.get("TEST_TIMEOUT", "900")), time.monotonic() - _STARTED
        )
        try:
            output = run_in_session(guest, rf"{gdir}\qemu-task.cmd", timeout)
        except SessionError as e:
            sys.stdout.write(e.log)
            sys.stderr.write(f"error: qemu-task.cmd: {e}\n")
            return 1
        sys.stdout.write(output)
        return 0
    finally:
        _collect(guest, gdir, collect)


def _put_stage(guest: Guest, gdir: str) -> None:
    """gdir, with the stage extracted into it if the test has one."""
    guest.powershell(f"New-Item -ItemType Directory -Path {ps_quote(gdir)} | Out-Null")
    if archive := _built_stage():
        guest.put(archive, rf"{gdir}\stage.tgz")
        guest.run(["tar.exe", "-xf", rf"{gdir}\stage.tgz", "-C", gdir])
        guest.powershell(f"Remove-Item -LiteralPath {ps_quote(rf'{gdir}\stage.tgz')}")


def _built_stage() -> Path | None:
    """The archive Bazel built of the stage (QEMU_STAGE), if the test has one."""
    if not (path := os.environ.get("QEMU_STAGE")):
        return None
    # Directory-based runfiles return the path whether it exists or not.
    if (
        (files := runfiles.Create()) is None
        or (located := files.Rlocation(path)) is None
        or not Path(located).is_file()
    ):
        raise VmError(f"the stage {path} is not in the test's runfiles")
    return Path(located)


def _collect(guest: Guest, gdir: str, names: Sequence[str]) -> None:
    """Best effort: a file the payload did not write is no error of its own."""
    if not names or not (outputs := os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")):
        return
    for name in names:
        target = Path(outputs, name)
        with contextlib.suppress(VmError):
            guest.get(rf"{gdir}\{name}", target)
