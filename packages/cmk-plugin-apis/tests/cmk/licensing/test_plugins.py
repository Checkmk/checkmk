#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.licensing.internal import entry_point_prefixes, LicenseUsageCounter


def test_entry_point_prefixes() -> None:
    assert entry_point_prefixes() == {LicenseUsageCounter: "license_usage_counter_"}
