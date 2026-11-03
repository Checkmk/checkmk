#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.licensing.usage_counters import discover_license_usage_counter_plugins


def test_discovered_license_usage_counter_plugins() -> None:
    assert {p.name for p in discover_license_usage_counter_plugins()} == set()
