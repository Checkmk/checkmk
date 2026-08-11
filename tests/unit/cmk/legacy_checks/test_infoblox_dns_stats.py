#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.legacy_checks.infoblox_dns_stats import check_infoblox_dns_stats


def test_empty_counters_treated_as_zero() -> None:
    # Some Infoblox devices return empty strings for counters that are not
    # populated; only the "successes" column is set here. These must be treated
    # as 0 instead of crashing the whole service (CMK-34647).
    result = check_infoblox_dns_stats(None, None, [["19149", "", "", "", "", ""]])
    assert result == (
        0,
        (
            "Since DNS process started: 19149 successful responses, 0 referrals, "
            "0 queries received using recursion, 0 queries failed - "
            "Queries: 0 for non-existent records, 0 for non-existent domain"
        ),
        [
            ("dns_successes", 19149),
            ("dns_referrals", 0),
            ("dns_recursion", 0),
            ("dns_failures", 0),
            ("dns_nxrrset", 0),
            ("dns_nxdomain", 0),
        ],
    )


def test_all_counters_populated() -> None:
    result = check_infoblox_dns_stats(None, None, [["100", "200", "300", "400", "500", "600"]])
    assert result == (
        0,
        (
            "Since DNS process started: 100 successful responses, 200 referrals, "
            "500 queries received using recursion, 600 queries failed - "
            "Queries: 300 for non-existent records, 400 for non-existent domain"
        ),
        [
            ("dns_successes", 100),
            ("dns_referrals", 200),
            ("dns_recursion", 500),
            ("dns_failures", 600),
            ("dns_nxrrset", 300),
            ("dns_nxdomain", 400),
        ],
    )
