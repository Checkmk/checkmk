#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.notification_plugins import asciimail

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
    assert asciimail._bulk_subject(contexts, hosts) == result
