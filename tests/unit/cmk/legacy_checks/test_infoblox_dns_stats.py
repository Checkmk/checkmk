#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.legacy_checks.infoblox_dns_stats import check_infoblox_dns_stats


def test_empty_counters_treated_as_zero() -> None:
    # Some Infoblox devices return empty strings for counters that are not
    # populated; only the "successes" column is set here. These must be treated
    # as 0 instead of crashing the whole service (CMK-34647).
    assert list(check_infoblox_dns_stats([["19149", "", "", "", "", ""]])) == [
        Result(
            state=State.OK,
            summary=(
                "Since DNS process started: 19149 successful responses, 0 referrals, "
                "0 queries received using recursion, 0 queries failed - "
                "Queries: 0 for non-existent records, 0 for non-existent domain"
            ),
        ),
        Metric("dns_successes", 19149),
        Metric("dns_referrals", 0),
        Metric("dns_recursion", 0),
        Metric("dns_failures", 0),
        Metric("dns_nxrrset", 0),
        Metric("dns_nxdomain", 0),
    ]


def test_all_counters_populated() -> None:
    assert list(check_infoblox_dns_stats([["100", "200", "300", "400", "500", "600"]])) == [
        Result(
            state=State.OK,
            summary=(
                "Since DNS process started: 100 successful responses, 200 referrals, "
                "500 queries received using recursion, 600 queries failed - "
                "Queries: 300 for non-existent records, 400 for non-existent domain"
            ),
        ),
        Metric("dns_successes", 100),
        Metric("dns_referrals", 200),
        Metric("dns_recursion", 500),
        Metric("dns_failures", 600),
        Metric("dns_nxrrset", 300),
        Metric("dns_nxdomain", 400),
    ]
