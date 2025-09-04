#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
+---------------------------------------------------------+
|              Achtung Alles Lookenskeepers!              |
|              =============================              |
|                                                         |
| The extend of the Check API is well documented, and the |
| result of careful negotiation. It should not be changed |
| light heartedly!                                        |
+---------------------------------------------------------+
"""

import pytest

from cmk.rulesets import v1


@pytest.mark.parametrize(
    "filename, expected_result",
    [
        (
            None,
            {
                "form_specs",
                "Help",
                "Label",
                "Message",
                "entry_point_prefixes",
                "rule_specs",
                "Title",
            },
        ),
        (
            "form_specs",
            {
                "Proxy",
                "SimpleLevels",
                "LevelsConfigModel",
                "MonitoredHost",
                "migrate_to_lower_integer_levels",
                "CascadingSingleChoice",
                "RegularExpression",
                "Integer",
                "String",
                "Float",
                "HostState",
                "DataSize",
                "FieldSize",
                "FixedValue",
                "DictGroup",
                "migrate_to_float_simple_levels",
                "MonitoredService",
                "Percentage",
                "IECMagnitude",
                "FormSpec",
                "ProxySchema",
                "InvalidElementMode",
                "Dictionary",
                "migrate_to_proxy",
                "LevelsType",
                "MultipleChoice",
                "Levels",
                "SimpleLevelsConfigModel",
                "List",
                "MultilineText",
                "SingleChoiceElement",
                "Prefill",
                "TimeSpan",
                "validators",
                "MultipleChoiceElement",
                "Metric",
                "migrate_to_upper_float_levels",
                "LevelDirection",
                "Password",
                "FileUpload",
                "TimePeriod",
                "CascadingSingleChoiceElement",
                "BooleanChoice",
                "SIMagnitude",
                "migrate_to_lower_float_levels",
                "ServiceState",
                "DictElement",
                "migrate_to_upper_integer_levels",
                "NoGroup",
                "PredictiveLevels",
                "migrate_to_time_period",
                "TimeMagnitude",
                "migrate_to_password",
                "MatchingScope",
                "SingleChoice",
                "InputHint",
                "InvalidElementValidator",
                "DefaultValue",
                "migrate_to_integer_simple_levels",
            },
        ),
    ],
)
def test_v1(filename: str | None, expected_result: set[str]) -> None:
    if not filename:
        assert set(v1.__all__) == expected_result
        return
    assert set(getattr(v1, filename).__all__) == expected_result
