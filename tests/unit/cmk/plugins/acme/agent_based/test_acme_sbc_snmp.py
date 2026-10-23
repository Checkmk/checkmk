#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.acme.agent_based.acme_sbc_snmp import check_acme_sbc_snmp, parse_acme_sbc_snmp


def test_check_acme_sbc_snmp() -> None:
    # Crash group 4889: the device delivers one row holding health score and redundancy state
    section = parse_acme_sbc_snmp([["100", "3"]])
    assert section is not None
    assert list(check_acme_sbc_snmp({"lower_levels": ("fixed", (75, 50))}, section)) == [
        Result(state=State.OK, summary="Health state: standby"),
        Result(state=State.OK, summary="Score: 100%"),
        Metric("health_state", 100.0),
    ]
