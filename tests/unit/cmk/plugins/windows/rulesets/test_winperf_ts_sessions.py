#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from contextlib import nullcontext
from typing import Any

import pytest

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.windows.rulesets.winperf_ts_sessions import rule_spec_winperf_ts_sessions


@pytest.mark.parametrize(
    "rule, expected_exception",
    [
        pytest.param({}, False, id="no rule"),
        pytest.param({"active": (10, 20)}, False, id="only active limits"),
        pytest.param({"inactive": (10, 20)}, False, id="only inactive limits"),
        pytest.param(
            {"active": (10, 20), "inactive": (5, 7)}, False, id="active and inactive limits"
        ),
        pytest.param({"Hello": "World"}, True, id="invalid key"),
    ],
)
def test_rule_spec_winperf_ts_sessions_levels_migrated(
    rule: dict[str, Any], expected_exception: bool
) -> None:
    """Test that rules from before ruleset migration are still readable"""
    valuespec = convert_to_legacy_rulespec(
        rule_spec_winperf_ts_sessions, Edition.CRE, lambda x: x
    ).valuespec

    context = pytest.raises(KeyError) if expected_exception else nullcontext()
    with context:
        valuespec.validate_datatype(rule, "")
        valuespec.validate_value(rule, "")
