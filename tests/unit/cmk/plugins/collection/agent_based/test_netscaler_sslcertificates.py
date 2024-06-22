#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.collection.agent_based import netscaler_sslcertificates

PARAMS = {
    "age_levels": (30, 10),
}

SECTION = {
    "cert1": 1123,
    "cert2": 7,
}


def test_check_netscaler_sslcertificates_ok() -> None:
    assert list(
        netscaler_sslcertificates.check_netscaler_sslcertificates(
            "cert1",
            PARAMS,
            SECTION,
        )
    ) == [
        Result(state=State.OK, summary="certificate valid for: 1123 days"),
        Metric("daysleft", 1123.0),
    ]


def test_check_netscaler_sslcertificates_crit() -> None:
    assert list(
        netscaler_sslcertificates.check_netscaler_sslcertificates(
            "cert2",
            PARAMS,
            SECTION,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="certificate valid for: 7 days (warn/crit below 30 days/10 days)",
        ),
        Metric("daysleft", 7.0),
    ]
