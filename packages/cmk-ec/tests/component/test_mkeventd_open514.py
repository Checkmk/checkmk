#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _run_without_mkeventd(
    tmp_path: Path, *args: str, program_name: str | None = None
) -> subprocess.CompletedProcess[str]:
    # There is no mkeventd next to this copy of mkeventd_open514, nor in the
    # current directory.
    program = tmp_path / "mkeventd_open514"
    shutil.copy(os.environ["MKEVENTD_OPEN514"], program)
    return subprocess.run(
        [str(program) if program_name is None else program_name, *args],
        executable=program,
        cwd=tmp_path,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


def _can_bind_privileged_ports() -> bool:
    if os.geteuid() == 0:
        return True
    try:
        start = int(Path("/proc/sys/net/ipv4/ip_unprivileged_port_start").read_text())
    except FileNotFoundError:  # Linux before 4.11, where the ports below 1024 need it
        return False
    return start <= 514


_needs_privilege_for_port_514 = pytest.mark.skipif(
    _can_bind_privileged_ports(), reason="binding port 514 needs no privilege here"
)

_NO_PRIVILEGE_FOR_SYSLOG_TCP = (
    "Cannot bind TCP socket for syslog to port 514: Permission denied (Does"
    " mkeventd_open514 have the capability CAP_NET_BIND_SERVICE, or is it SUID root?"
    ' Is the filesystem mounted without "nosuid"?)\n'
)


def test_failing_execution_of_mkeventd_is_an_error(tmp_path: Path) -> None:
    result = _run_without_mkeventd(tmp_path)

    assert (result.returncode, result.stderr) == (
        1,
        "Cannot execute mkeventd: No such file or directory\n",
    )


def test_program_name_without_path_is_an_error(tmp_path: Path) -> None:
    result = _run_without_mkeventd(tmp_path, program_name="mkeventd_open514")

    assert (result.returncode, result.stderr) == (
        1,
        "Cannot find mkeventd: Called without a path\n",
    )


@pytest.mark.parametrize("option", ["--syslog-fd", "--syslog-tcp-fd", "--snmptrap-fd"])
def test_trailing_fd_option_without_value_is_ignored(tmp_path: Path, option: str) -> None:
    result = _run_without_mkeventd(tmp_path, option)

    assert (result.returncode, result.stderr) == (
        1,
        "Cannot execute mkeventd: No such file or directory\n",
    )


@_needs_privilege_for_port_514
def test_binding_without_the_privilege_asks_for_it(tmp_path: Path) -> None:
    result = _run_without_mkeventd(tmp_path, "--syslog-tcp", "--syslog-tcp-fd", "4")

    assert (result.returncode, result.stderr) == (1, _NO_PRIVILEGE_FOR_SYSLOG_TCP)


@_needs_privilege_for_port_514
def test_fd_option_takes_its_value_after_an_equals_sign(tmp_path: Path) -> None:
    result = _run_without_mkeventd(tmp_path, "--syslog-tcp", "--syslog-tcp-fd=4")

    assert (result.returncode, result.stderr) == (1, _NO_PRIVILEGE_FOR_SYSLOG_TCP)
