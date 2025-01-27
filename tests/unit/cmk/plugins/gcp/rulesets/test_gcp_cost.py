#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.gcp.rulesets.gcp_cost import migrate_to_float_simple_levels_ignoring_predictive


def test_rule_migrate_predictive():
    predictive = {
        "__injected__": None,
        "period": "wday",
        "horizon": 90,
        "levels_upper": ("absolute", (0.0, 0.0)),
    }

    migrated_once = migrate_to_float_simple_levels_ignoring_predictive(predictive)
    assert migrated_once == ("no_levels", None)
    migrated_twice = migrate_to_float_simple_levels_ignoring_predictive(migrated_once)
    assert migrated_twice == migrated_once
