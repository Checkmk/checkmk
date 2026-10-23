#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import time_machine

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.acme.agent_based.acme_certificates import check_acme_certificates, CheckParamT


def test_check_acme_certificates_reports_expired_certificate() -> None:
    # A root certificate that expired about 16 months before the check ran.
    section = {
        "BaltimoreRoot-2025-05": (
            "May 12 18:46:00 2000 GMT",
            "May 12 23:59:00 2025 GMT",
            "/C=IE/O=Baltimore/OU=CyberTrust/CN=Baltimore CyberTrust Root",
        )
    }
    with time_machine.travel(datetime.datetime(2026, 9, 16, tzinfo=datetime.UTC), tick=False):
        results = list(
            check_acme_certificates(
                "BaltimoreRoot-2025-05",
                CheckParamT(expire_lower=("fixed", (604800.0, 2592000.0))),
                section,
            )
        )

    assert results[0] == Result(state=State.CRIT, summary="Expired 1 year 126 days ago")
    assert isinstance(results[1], Metric)
    assert results[1].name == "certificate_expiration_time"
    assert results[1].value < 0
