#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from argparse import Namespace
from collections.abc import Sequence

import pytest

from cmk.plugins.emailchecks.lib import check_mailboxes


def test_parse_arguments_empty_mailbox_arg(capsys: pytest.CaptureFixture[str]) -> None:
    parser = argparse.ArgumentParser(description="parser")
    argv = [
        "--warn-age-oldest",
        "5",
        "--crit-age-oldest",
        "10",
        "--mailbox",
    ]

    parser = check_mailboxes.create_argument_parser()

    with pytest.raises(SystemExit) as err:
        parser.parse_args(argv)

    assert err.value.code == 2

    captured = capsys.readouterr()
    assert "error: argument --mailbox: expected at least one argument" in captured.err


@pytest.mark.parametrize(
    "argv, expected_result",
    [
        pytest.param(
            ["--warn-age-oldest", "5", "--crit-age-oldest", "10", "--mailbox", "inbox"],
            Namespace(
                warn_age_oldest=5,
                crit_age_oldest=10,
                warn_age_newest=None,
                crit_age_newest=None,
                warn_count=None,
                crit_count=None,
                mailbox=["inbox"],
                retrieve_max=None,
            ),
            id="One mailbox",
        ),
        pytest.param(
            ["--warn-age-oldest", "5", "--crit-age-oldest", "10", "--mailbox", "inbox", "sent"],
            Namespace(
                warn_age_oldest=5,
                crit_age_oldest=10,
                warn_age_newest=None,
                crit_age_newest=None,
                warn_count=None,
                crit_count=None,
                mailbox=["inbox", "sent"],
                retrieve_max=None,
            ),
            id="Mailboxes on single option",
        ),
        pytest.param(
            [
                "--warn-age-oldest",
                "5",
                "--crit-age-oldest",
                "10",
                "--mailbox",
                "inbox",
                "--mailbox",
                "sent",
            ],
            Namespace(
                warn_age_oldest=5,
                crit_age_oldest=10,
                warn_age_newest=None,
                crit_age_newest=None,
                warn_count=None,
                crit_count=None,
                mailbox=["inbox", "sent"],
                retrieve_max=None,
            ),
            id="Mailboxes on multiple option",
        ),
    ],
)
def test_parse_arguments(argv: Sequence[str], expected_result: Namespace) -> None:
    parser = argparse.ArgumentParser(description="parser")
    parser = check_mailboxes.create_argument_parser()
    result = parser.parse_args(argv)
    assert result == expected_result
