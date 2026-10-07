#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
import socket
import tempfile
from pathlib import Path

import pytest

from cmk.events.log_to_history import (
    log_to_history,
    notification_message,
    notification_progress_message,
    notification_result_message,
    SanitizedLivestatusLogStr,
)
from cmk.events.notification_result import (
    NotificationContext,
    NotificationPluginName,
    NotificationResultCode,
)

_MAIL = NotificationPluginName("mail")
_HOST_CONTEXT = NotificationContext({"CONTACTNAME": "harri", "HOSTNAME": "test"})


def test_notification_result_message() -> None:
    """Regression test for Werk #8783"""
    plugin = NotificationPluginName("bulk asciimail")
    exit_code = NotificationResultCode(0)
    output: list[str] = []
    actual = notification_result_message(
        plugin, NotificationContext({"CONTACTNAME": "harri", "HOSTNAME": "test"}), exit_code, output
    )
    fields = "harri;test;OK;bulk asciimail;;"
    expected = f"HOST NOTIFICATION RESULT: {fields}"
    assert actual == expected


def test_service_notification_message_names_the_service() -> None:
    context = NotificationContext(
        {
            "CONTACTNAME": "harri",
            "HOSTNAME": "test",
            "SERVICEDESC": "CPU load",
            "SERVICESTATE": "CRITICAL",
            "SERVICEOUTPUT": "load too high",
        }
    )

    assert (
        notification_message(_MAIL, context)
        == "SERVICE NOTIFICATION: harri;test;CPU load;CRITICAL;mail;load too high"
    )


def test_progress_message_reports_exit_code_as_state() -> None:
    assert (
        notification_progress_message(
            _MAIL, _HOST_CONTEXT, NotificationResultCode(1), "retrying later"
        )
        == "HOST NOTIFICATION PROGRESS: harri;test;WARNING;mail;retrying later"
    )


def test_result_message_shows_last_output_line_and_all_lines_as_comment() -> None:
    assert (
        notification_result_message(
            _MAIL, _HOST_CONTEXT, NotificationResultCode(2), ["connecting", "refused"]
        )
        == "HOST NOTIFICATION RESULT: harri;test;CRITICAL;mail;refused;connecting -- refused"
    )


def test_result_message_escapes_field_separator_in_output() -> None:
    assert (
        notification_result_message(_MAIL, _HOST_CONTEXT, NotificationResultCode(3), ["a;b"])
        == "HOST NOTIFICATION RESULT: harri;test;UNKNOWN;mail;a%3Bb;a%3Bb"
    )


def _receive_command(connection: socket.socket) -> str:
    received = b""
    while not received.endswith(b"\n\n"):
        if not (chunk := connection.recv(4096)):
            break
        received += chunk
    return received.decode("utf-8")


def test_message_is_sent_to_the_local_monitoring_core(monkeypatch: pytest.MonkeyPatch) -> None:
    # A short site root keeps the socket path within the AF_UNIX length limit, tmp_path may not.
    with tempfile.TemporaryDirectory(prefix="ls", dir="/tmp") as site_root:
        monkeypatch.setenv("OMD_ROOT", site_root)
        monkeypatch.setenv("OMD_SITE", "mysite")
        socket_path = Path(site_root, "tmp/run/live")
        socket_path.parent.mkdir(parents=True)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as core:
            core.bind(str(socket_path))
            core.listen()
            core.settimeout(5)
            log_to_history(SanitizedLivestatusLogStr("HOST NOTIFICATION: harri;test;OK;mail;"))
            connection, _address = core.accept()
            with connection:
                connection.settimeout(5)
                received = _receive_command(connection)

    assert re.fullmatch(r"COMMAND \[\d+\] LOG;HOST NOTIFICATION: harri;test;OK;mail;\n\n", received)


def test_message_is_dropped_outside_a_site(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("OMD_ROOT", raising=False)

    with caplog.at_level(logging.INFO, logger="cmk.events.log_to_history"):
        log_to_history(SanitizedLivestatusLogStr("HOST NOTIFICATION: harri;test;OK;mail;"))

    assert "Command was: LOG;HOST NOTIFICATION: harri;test;OK;mail;" in caplog.text
