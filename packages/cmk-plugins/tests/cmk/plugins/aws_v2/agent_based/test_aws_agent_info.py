#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, State
from cmk.plugins.aws_v2.agent_based.aws_agent_info import (
    check_aws_agent_info,
    parse_aws_agent_info,
    Section,
)


def _section(*lines: str) -> Section:
    return parse_aws_agent_info([[line] for line in lines])


def test_reached_accounts_are_counted() -> None:
    section = _section('{"status": "ok", "account": "111"}', '{"status": "ok", "account": "222"}')

    assert list(check_aws_agent_info(section)) == [
        Result(state=State.OK, summary="Accounts reached: 2")
    ]


def test_unreachable_account_is_crit_with_its_reason() -> None:
    section = _section(
        '{"status": "ok", "account": "111"}',
        '{"status": "error", "account": "999", "reason": "Access denied"}',
    )

    assert list(check_aws_agent_info(section)) == [
        Result(state=State.OK, summary="Accounts reached: 1"),
        Result(state=State.CRIT, summary="Account 999 unreachable", details="Access denied"),
    ]


def test_failed_run_is_crit_with_its_reason() -> None:
    section = _section('{"status": "error", "reason": "The login failed"}')

    assert list(check_aws_agent_info(section)) == [
        Result(state=State.OK, summary="Accounts reached: 0"),
        Result(state=State.CRIT, summary="The login failed"),
    ]


def test_info_rows_do_not_change_the_state() -> None:
    section = _section(
        '{"status": "ok", "account": "111"}',
        '{"status": "info", "account": "111", "reason": "Region is not enabled in this account",'
        ' "region": "me-central-1"}',
    )

    assert list(check_aws_agent_info(section)) == [
        Result(state=State.OK, summary="Accounts reached: 1"),
        Result(
            state=State.OK,
            notice="Account 111, me-central-1: Region is not enabled in this account",
        ),
    ]
