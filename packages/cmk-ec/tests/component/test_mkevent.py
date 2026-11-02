#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Runs mkevent, with a FIFO standing in for the event pipe of the Event Console"""

import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest


def _run_mkevent(
    *args: str, argv0: str | None = None, env: Mapping[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    mkevent = os.environ["MKEVENT"]
    return subprocess.run(
        [argv0 or mkevent, *args],
        executable=mkevent,
        capture_output=True,
        encoding="utf-8",
        env=env,
        timeout=30,
        check=False,
    )


def _send_event(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], bytes]:
    pipe = tmp_path / "events"
    os.mkfifo(pipe)
    # With a reader, mkevent doesn't wait, and reading hits EOF once mkevent is gone.
    reader = os.open(pipe, os.O_RDONLY | os.O_NONBLOCK)
    try:
        result = _run_mkevent("-P", str(pipe), *args)
        received = b""
        while chunk := os.read(reader, 65536):
            received += chunk
        return result, received
    finally:
        os.close(reader)


def test_message_is_written_as_one_line(tmp_path: Path) -> None:
    result, received = _send_event(tmp_path, "something happened")

    assert (result.returncode, received) == (0, b"something happened\n")


def test_notification_is_written_as_syslog_message(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path, "-n", "1", "", "2", "myhost", "myservice", "it broke", "10", "admin"
    )

    assert result.returncode == 0
    assert re.fullmatch(rb"<10>@\d+;10;admin; myhost myservice: it broke\n", received)


def test_host_notification_is_written_as_syslog_message(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path, "-n", "1", "", "1", "myhost", "", "it's down", "10", "admin"
    )

    # Host state DOWN (1) is mapped like service state CRIT (2): priority crit (2).
    assert result.returncode == 0
    assert re.fullmatch(rb"<10>@\d+;10;admin; myhost HOST: it's down\n", received)


@pytest.mark.parametrize(
    "state, service, header",
    [
        pytest.param("0", "myservice", b"<13>@", id="service OK is notice"),
        pytest.param("1", "myservice", b"<12>@", id="service WARN is warning"),
        pytest.param("2", "myservice", b"<10>@", id="service CRIT is crit"),
        pytest.param("3", "myservice", b"<11>@", id="service UNKNOWN is err"),
        pytest.param("0", "", b"<13>@", id="host UP is notice"),
        pytest.param("1", "", b"<10>@", id="host DOWN is crit"),
        pytest.param("2", "", b"<11>@", id="host UNREACHABLE is err"),
    ],
)
def test_notification_state_is_mapped_to_syslog_priority(
    tmp_path: Path, state: str, service: str, header: bytes
) -> None:
    result, received = _send_event(
        tmp_path, "-n", "1", "", state, "myhost", service, "it changed", "10", "admin"
    )

    # With facility user (1), the priority is 8 plus the severity.
    assert result.returncode == 0
    assert received.startswith(header)


def test_unset_service_sl_and_contact_fall_back_to_host_ones(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path,
        "-n",
        "1",
        "",
        "2",
        "myhost",
        "myservice",
        "it broke",
        "$_SERVICEEC_SL$",
        "$_SERVICEEC_CONTACT$",
        "20",
        "hostadmin",
    )

    assert result.returncode == 0
    assert re.fullmatch(rb"<10>@\d+;20;hostadmin; myhost myservice: it broke\n", received)


def test_unset_sl_and_contact_become_0_and_empty(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path,
        "-n",
        "1",
        "",
        "2",
        "myhost",
        "myservice",
        "it broke",
        "$_SERVICEEC_SL$",
        "$_SERVICEEC_CONTACT$",
        "$_HOSTEC_SL$",
        "$_HOSTEC_CONTACT$",
    )

    assert result.returncode == 0
    assert re.fullmatch(rb"<10>@\d+;0;; myhost myservice: it broke\n", received)


def test_pipe_is_looked_up_below_omd_root(tmp_path: Path) -> None:
    result = _run_mkevent("something happened", env={"OMD_ROOT": str(tmp_path)})

    assert (result.returncode, result.stderr) == (
        1,
        f"Cannot open event pipe '{tmp_path}/tmp/run/mkeventd/events': No such file or directory\n",
    )


def test_pipe_is_looked_up_in_site_of_mkevent() -> None:
    result = _run_mkevent("something happened", argv0="/omd/sites/no-such-site/bin/mkevent", env={})

    assert (result.returncode, result.stderr) == (
        1,
        (
            "Cannot open event pipe '/omd/sites/no-such-site/tmp/run/mkeventd/events': "
            "No such file or directory\n"
        ),
    )


def test_empty_pipe_falls_back_to_site_of_mkevent() -> None:
    result = _run_mkevent(
        "-P", "", "something happened", argv0="/omd/sites/no-such-site/bin/mkevent", env={}
    )

    assert (result.returncode, result.stderr) == (
        1,
        (
            "Cannot open event pipe '/omd/sites/no-such-site/tmp/run/mkeventd/events': "
            "No such file or directory\n"
        ),
    )


def test_pipe_is_not_derived_from_other_paths_below_omd_sites() -> None:
    # mkevent once cut the length of "/bin/mkevent" off any such path, aborting for this one.
    result = _run_mkevent("something happened", argv0="/omd/sites/", env={})

    assert (result.returncode, result.stderr) == (
        1,
        "Cannot open event pipe '': No such file or directory\n",
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param([], id="no arguments"),
        pytest.param(["-P"], id="pipe option alone"),
        pytest.param(["-P", "events"], id="pipe without message"),
    ],
)
def test_too_few_arguments_are_a_usage_error(args: list[str]) -> None:
    result = _run_mkevent(*args)

    assert (result.returncode, result.stderr) == (
        1,
        "Usage: mkevent [-P PIPE] 'Text of the message'\n",
    )
