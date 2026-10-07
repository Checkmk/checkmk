#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import email
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from cmk.notification_plugins import asciimail
from cmk.testlib.notification_plugins import exit_code

_BULK_SUBJECT = "BULK: $COUNT_NOTIFICATIONS$ notifications for $COUNT_HOSTS$ hosts"


def _context(hostname: str, *, bulk_subject: str | None = None) -> dict[str, str]:
    context = {
        "HOSTNAME": hostname,
        "HOSTTAGS": "/wato/lan cmk-agent ip-v4 prod site:heute tcp wato",
        "SUBJECT": f"SINGLE: {hostname}",
    }
    if bulk_subject is not None:
        context["PARAMETER_BULK_SUBJECT"] = bulk_subject
    return context


@pytest.mark.parametrize(
    "contexts, hosts, result",
    [
        pytest.param(
            [_context("host1")],
            {"host1"},
            "SINGLE: host1",
            id="single context uses per-notification subject",
        ),
        pytest.param(
            [
                _context("host1", bulk_subject=_BULK_SUBJECT),
                _context("host1", bulk_subject=_BULK_SUBJECT),
                _context("host1", bulk_subject=_BULK_SUBJECT),
            ],
            {"host1"},
            "BULK: 3 notifications for 1 hosts",
            id="single-host bulk uses bulk subject (issue 1)",
        ),
        pytest.param(
            [
                _context("host1", bulk_subject=_BULK_SUBJECT),
                _context("host1", bulk_subject=_BULK_SUBJECT),
                _context("host2", bulk_subject=_BULK_SUBJECT),
            ],
            {"host1", "host2"},
            "BULK: 3 notifications for 2 hosts",
            id="multi-host bulk counts every notification (issue 2)",
        ),
    ],
)
def test_bulk_subject(contexts: list[dict[str, str]], hosts: set[str], result: str) -> None:
    assert asciimail._bulk_subject(contexts, hosts) == result  # noqa: SLF001


def _notification_context(**overrides: str) -> dict[str, str]:
    context = {
        "WHAT": "HOST",
        "NOTIFICATIONTYPE": "PROBLEM",
        "HOSTNAME": "heute",
        "HOSTALIAS": "Today",
        "HOSTADDRESS": "127.0.0.1",
        "HOSTSHORTSTATE": "DOWN",
        "PREVIOUSHOSTHARDSHORTSTATE": "UP",
        "HOSTOUTPUT": "No response",
        "HOSTPERFDATA": "rta=0",
        "LONGHOSTOUTPUT": "",
        "SERVICEDESC": "CPU load",
        "SERVICESHORTSTATE": "WARN",
        "PREVIOUSSERVICEHARDSHORTSTATE": "OK",
        "SERVICEOUTPUT": "load 5",
        "SERVICEPERFDATA": "load=5",
        "LONGSERVICEOUTPUT": "",
        "EVENT_TXT": "UP -> DOWN",
        "CONTACTEMAIL": "test@example.com",
        "PARAMETER_FROM_ADDRESS": "from@example.com",
    }
    context.update(overrides)
    return context


def test_default_common_body_identifies_the_host() -> None:
    body = asciimail.construct_content(_notification_context())

    assert body.startswith("Host:     heute\nAlias:    Today\nAddress:  127.0.0.1\n")


# fmt: off
@pytest.mark.parametrize(
    "overrides, expected_body",
    [
        pytest.param({}, "Event:    UP -> DOWN\nOutput:   No response\nPerfdata: rta=0\n\n", id="host"),
        pytest.param({"WHAT": "SERVICE", "EVENT_TXT": "OK -> WARN"}, "Service:  CPU load\nEvent:    OK -> WARN\nOutput:   load 5\nPerfdata: load=5\n\n", id="service"),
        pytest.param({"ALERTHANDLERNAME": "restart", "ALERTHANDLEROUTPUT": "done"}, "Alert handler: restart\nHandler output: done\n", id="host alert handler"),
        pytest.param({"WHAT": "SERVICE", "ALERTHANDLERNAME": "restart", "ALERTHANDLEROUTPUT": "done"}, "Service:  CPU load\nAlert handler: restart\nHandler output: done\n", id="service alert handler"),
    ],
)
# fmt: on
def test_default_event_body(overrides: dict[str, str], expected_body: str) -> None:
    body = asciimail.construct_content(_notification_context(PARAMETER_COMMON_BODY="", **overrides))

    assert body == expected_body


# fmt: off
@pytest.mark.parametrize(
    "overrides, expected_body",
    [
        pytest.param({"PARAMETER_HOST_BODY": "$HOSTOUTPUT$"}, "heute\nNo response", id="host"),
        pytest.param({"WHAT": "SERVICE", "PARAMETER_SERVICE_BODY": "$SERVICEOUTPUT$"}, "heute\nload 5", id="service"),
    ],
)
# fmt: on
def test_configured_bodies_replace_defaults(overrides: dict[str, str], expected_body: str) -> None:
    body = asciimail.construct_content(
        _notification_context(PARAMETER_COMMON_BODY="$HOSTNAME$\n", **overrides)
    )

    assert body == expected_body


def test_escaped_line_breaks_in_body_become_real_line_breaks() -> None:
    body = asciimail.construct_content(_notification_context(LONGHOSTOUTPUT="first\\nsecond"))

    assert body.endswith("first\nsecond\n")


# fmt: off
@pytest.mark.parametrize(
    "overrides, expected_subject",
    [
        pytest.param({}, "Check_MK: heute - UP -> DOWN", id="host default"),
        pytest.param({"WHAT": "SERVICE", "EVENT_TXT": "OK -> WARN"}, "Check_MK: heute/CPU load OK -> WARN", id="service default"),
        pytest.param({"PARAMETER_HOST_SUBJECT": "$HOSTNAME$ is $HOSTSHORTSTATE$"}, "heute is DOWN", id="host custom"),
        pytest.param({"WHAT": "SERVICE", "PARAMETER_SERVICE_SUBJECT": "$SERVICEDESC$ broke"}, "CPU load broke", id="service custom"),
    ],
)
# fmt: on
def test_subject_is_stored_in_context(overrides: dict[str, str], expected_subject: str) -> None:
    context = _notification_context(**overrides)

    asciimail.construct_content(context)

    assert context["SUBJECT"] == expected_subject


@pytest.mark.usefixtures("fake_sendmail")
def test_main_spools_mail_and_exits_successfully(
    notify_context: Callable[[Mapping[str, str]], None], capsys: pytest.CaptureFixture[str]
) -> None:
    notify_context(_notification_context())

    assert (exit_code(asciimail.main), capsys.readouterr().out) == (
        0,
        "Spooled mail to local mail transmission agent\n",
    )


def test_main_sends_mail_with_configured_headers(
    fake_sendmail: Path, notify_context: Callable[[Mapping[str, str]], None]
) -> None:
    notify_context(
        _notification_context(
            PARAMETER_FROM_DISPLAY_NAME="Checkmk",
            PARAMETER_REPLY_TO_ADDRESS="reply@example.com",
        )
    )

    exit_code(asciimail.main)

    message = email.message_from_string(fake_sendmail.read_text())
    assert (message["Subject"], message["To"], message["From"], message["Reply-To"]) == (
        "Check_MK: heute - UP -> DOWN",
        "test@example.com",
        "Checkmk <from@example.com>",
        "reply@example.com",
    )


def test_main_sends_rendered_body(
    fake_sendmail: Path, notify_context: Callable[[Mapping[str, str]], None]
) -> None:
    notify_context(_notification_context(PARAMETER_HOST_BODY="Body $HOSTNAME$"))

    exit_code(asciimail.main)

    payload = email.message_from_string(fake_sendmail.read_text()).get_payload(decode=True)
    assert isinstance(payload, bytes)
    assert payload.decode() == "Host:     heute\nAlias:    Today\nAddress:  127.0.0.1\nBody heute"


@pytest.mark.usefixtures("fake_sendmail")
def test_main_rejects_empty_recipient(
    notify_context: Callable[[Mapping[str, str]], None], capsys: pytest.CaptureFixture[str]
) -> None:
    notify_context(_notification_context(CONTACTEMAIL=""))

    assert (exit_code(asciimail.main), capsys.readouterr().out) == (
        2,
        "Cannot send ASCII email: empty destination email address\n",
    )


@pytest.mark.usefixtures("failing_sendmail")
def test_main_send_failure_is_final(
    notify_context: Callable[[Mapping[str, str]], None], capsys: pytest.CaptureFixture[str]
) -> None:
    notify_context(_notification_context())

    assert (exit_code(asciimail.main), capsys.readouterr().err) == (
        2,
        "Unhandled exception: sendmail returned with exit code: 3; boom\n; \n",
    )
