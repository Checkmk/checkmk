#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.hivemanager_ng_devices import (
    check_hivemanager_ng_devices,
    parse_hivemanager_ng_devices,
)


def test_check_hivemanager_ng_devices_vanished_device() -> None:
    parsed = parse_hivemanager_ng_devices(
        [
            [
                "osVersion::10.0.0.2",
                "ip::10.0.0.1",
                "hostName::AP-1",
                "lastUpdated::2026-11-02T04:58:27.000+0000",
                "activeClients::0",
                "connected::True",
                "serialId::00000000000001",
            ]
        ]
    )

    assert list(check_hivemanager_ng_devices("AP-2", {"max_clients": (25, 50)}, parsed)) == [
        (2, "No data for device.")
    ]
