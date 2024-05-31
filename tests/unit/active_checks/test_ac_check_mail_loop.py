#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

# pylint: disable=protected-access
from types import ModuleType

import pytest

from tests.unit.import_module_hack import import_module_hack

from cmk.utils.mailbox import _active_check_main_core


@pytest.fixture(name="check_mail_loop", scope="module")
def fixture_check_mail_loop() -> ModuleType:
    return import_module_hack("active_checks/check_mail_loop")


def test_ac_check_mail_main_loop_failed_to_send_mail(check_mail_loop: ModuleType) -> None:
    state, info, perf = _active_check_main_core(
        check_mail_loop.create_argument_parser(),
        check_mail_loop.check_mail_roundtrip,
        [
            "--send-server",
            "foo",
            "--fetch-server",
            "bar",
            "--fetch-username",
            "baz",
            "--fetch-password",
            "passw",
            "--mail-from",
            "from",
            "--mail-to",
            "to",
        ],
    )
    assert state == 3
    assert info.startswith("Failed to")
    assert perf is None


@pytest.mark.parametrize(
    "warning, critical, expected_mails, fetched_mails, expected_result",
    [
        (
            None,
            3600,
            {},
            {},
            (0, "Did not receive any new mail", []),
        ),
        # No received mails
        (
            None,
            3600,
            {"0-123": (0, 123)},
            {},
            (
                2,
                "Did not receive any new mail, Lost: 1 (Did not arrive within 3600 seconds)",
                [],
            ),
        ),
        (
            None,
            1000,
            {"0-123": (0, 123)},
            {},
            (
                2,
                "Did not receive any new mail, Lost: 1 (Did not arrive within 1000 seconds)",
                [],
            ),
        ),
        (
            None,
            1000,
            {
                "0-123": (0, 123),
                "0-Bar": (0, "Bar"),
            },
            {},
            (
                2,
                "Did not receive any new mail, Lost: 2 (Did not arrive within 1000 seconds)",
                [],
            ),
        ),
        (
            None,
            2**64,
            {
                "0-123": (0, 123),
            },
            {},
            (
                0,
                "Did not receive any new mail, Currently waiting for 1 mails",
                [],
            ),
        ),
        (
            None,
            2**64,
            {
                "0-123": (0, 123),
                "0-Bar": (0, "Bar"),
            },
            {},
            (
                0,
                "Did not receive any new mail, Currently waiting for 2 mails",
                [],
            ),
        ),
        # No expected mails
        (
            None,
            3600,
            {},
            {
                "0-123": (0, 123),
            },
            (0, "Did not receive any new mail", []),
        ),
        # Both fetched and expected mails
        (
            None,
            3600,
            {
                "0-123": (0, 123),
                "0-456": (0, 456),
            },
            {
                "0-123": (0, 123),
                "0-456": (0, 456),
            },
            (
                0,
                "Received 2 mails within average of 289 seconds",
                [("duration", 289.5, "", 3600)],
            ),
        ),
        (
            None,
            3600,
            {
                "0-123": (0, 123),
                "0-789": (0, 789),
            },
            {
                "0-123": (0, 123),
                "0-456": (0, 456),
            },
            (
                2,
                "Mail received within 123 seconds, Lost: 1 (Did not arrive within 3600 seconds)",
                [("duration", 123, "", 3600)],
            ),
        ),
    ],
)
def test_ac_check_mail_loop(
    check_mail_loop: ModuleType,
    warning: object,
    critical: int,
    expected_mails: dict[str, object],
    fetched_mails: dict[str, object],
    expected_result: tuple[int, str, Sequence[object]],
) -> None:
    state, info, perf = check_mail_loop.check_mails(
        warning, critical, expected_mails.copy(), fetched_mails.copy()
    )
    e_state, e_info, e_perf = expected_result
    assert state == e_state
    assert info == e_info
    assert perf == e_perf


@pytest.mark.parametrize(
    "subject",
    [
        "subject",
        "Re: subject",
        "WG: subject",
        "Re: WG: Re: Re: subject",
        "RE: Wg: re: subject",
    ],
)
def test_regex_pattern(check_mail_loop: ModuleType, subject: str) -> None:
    assert check_mail_loop.subject_regex(subject).match(f"{subject} 123 45").groups() == (
        "123",
        "45",
    )


_ = __name__ == "__main__" and pytest.main(["-svv", "-T=unit", __file__])
