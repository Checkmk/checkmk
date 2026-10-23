#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.plugins.redfish.lib import parse_redfish_multiple


def test_parse_redfish_multiple_stringifies_numeric_identifiers() -> None:
    entry = {
        "@odata.id": "/redfish/v1/Chassis/1/Power",
        "@odata.type": "#Power.v1_5_0.Power",
        "Id": 1,
        "PowerControl": [{"MemberId": 0, "PowerConsumedWatts": 230}],
    }

    parsed = parse_redfish_multiple([[json.dumps(entry)]])

    assert parsed == {
        "/redfish/v1/Chassis/1/Power": {
            "@odata.id": "/redfish/v1/Chassis/1/Power",
            "@odata.type": "#Power.v1_5_0.Power",
            "Id": "1",
            "PowerControl": [{"MemberId": "0", "PowerConsumedWatts": 230}],
        }
    }
