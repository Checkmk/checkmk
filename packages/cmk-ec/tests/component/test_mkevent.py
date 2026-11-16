#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Runs mkevent, with a FIFO standing in for the event pipe of the Event Console"""

import os
import re
import subprocess
from pathlib import Path

import pytest


def _run_mkevent(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [os.environ["MKEVENT"], *args],
        capture_output=True,
        encoding="utf-8",
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


def test_long_message_is_truncated(tmp_path: Path) -> None:
    # Only the length: mkevent once read past its unterminated buffer for such a message, which
    # showed only if no NUL byte happened to follow the buffer on the stack.
    result, received = _send_event(tmp_path, "x" * 10000)

    assert (result.returncode, received) == (0, b"x" * 8191 + b"\n")


@pytest.mark.parametrize(
    "character",
    [
        # Cutting after 8191 bytes would split the 4096th one after its 1st byte.
        pytest.param("ä", id="2 bytes"),
        # Cutting after 8191 bytes would split the 2048th one after its 3rd byte.
        pytest.param("😀", id="4 bytes"),
    ],
)
def test_long_message_is_not_cut_within_a_character(tmp_path: Path, character: str) -> None:
    result, received = _send_event(tmp_path, character * 5000)

    encoded = character.encode()
    assert (result.returncode, received) == (0, encoded * (8191 // len(encoded)) + b"\n")


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


def test_negative_sl_is_written_with_its_sign(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path, "-n", "1", "", "2", "myhost", "myservice", "it broke", "-5", "admin"
    )

    assert result.returncode == 0
    assert re.fullmatch(rb"<10>@\d+;-5;admin; myhost myservice: it broke\n", received)


def test_long_notification_text_is_truncated(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path, "-n", "1", "", "2", "myhost", "myservice", "x" * 10000, "10", "admin"
    )

    assert (result.returncode, len(received)) == (0, 8192)
    assert re.fullmatch(rb"<10>@\d+;10;admin; myhost myservice: x+\n", received)


def test_long_notification_text_is_not_cut_within_a_character(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path, "-n", "1", "", "2", "myhost", "myservice", "ä" * 5000, "10", "admin"
    )

    # With a header of even length, cutting after 8191 bytes would split an "ä".
    assert (result.returncode, len(received)) == (0, 8191)
    assert re.fullmatch(r"<10>@\d+;10;admin; myhost myservice: ä+\n", received.decode("utf-8"))
