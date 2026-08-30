#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.fireeye_mailq import (
    check_fireeye_mailq,
    dicsover_fireeye_mailq,
    parse_fireeye_mailq,
    Section,
)


@pytest.fixture(scope="module", name="section")
def _get_section() -> Section:
    section = parse_fireeye_mailq([["0", "0", "0", "3", "5"]])
    assert section is not None
    return section


def test_discover_somehting(section: Section) -> None:
    assert list(dicsover_fireeye_mailq(section)) == [Service()]


def test_check(section: Section) -> None:
    params: dict[str, tuple[float, float] | None] = {
        # deferred not present
        "hold": (1, 5),  # OK case
        "active": (1, 5),  # WARN case
        "drop": (1, 5),  # CRIT case
    }
    assert list(check_fireeye_mailq(params, section)) == [
        Result(state=State.OK, summary="Mails in deferred queue: 0"),
        Metric("mail_queue_deferred_length", 0),
        Result(state=State.OK, summary="Mails in hold queue: 0"),
        Metric("mail_queue_hold_length", 0, levels=(1, 5)),
        Result(state=State.OK, summary="Mails in incoming queue: 0"),
        Metric("mail_queue_incoming_length", 0),
        Result(state=State.WARN, summary="Mails in active queue: 3 (warn/crit at 1/5)"),
        Metric("mail_queue_active_length", 3, levels=(1, 5)),
        Result(state=State.CRIT, summary="Mails in drop queue: 5 (warn/crit at 1/5)"),
        Metric("mail_queue_drop_length", 5, levels=(1, 5)),
    ]
