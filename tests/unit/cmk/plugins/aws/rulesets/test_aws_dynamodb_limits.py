#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.aws.rulesets.aws_dynamodb_limits import rule_spec_aws_dynamodb_limits


def _migrate(value: object) -> Mapping[str, object]:
    migrate = rule_spec_aws_dynamodb_limits.parameter_form().migrate
    assert migrate is not None
    return migrate(value)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param({"number_of_tables": ("no_levels", None)}, id="no levels"),
        pytest.param(
            {
                "read_capacity": (
                    "set_levels",
                    {
                        "absolute": ("aws_limit_value", 1000),
                        "percentage": {"warn": 80.0, "crit": 90.0},
                    },
                )
            },
            id="set levels",
        ),
    ],
)
def test_migrate_keeps_formspec_values(value: Mapping[str, object]) -> None:
    assert _migrate(value) == value


def test_migrate_converts_valuespec_values() -> None:
    assert _migrate(
        {"number_of_tables": (None, None, None), "write_capacity": (500, 70.0, 85.0)}
    ) == {
        "number_of_tables": ("no_levels", None),
        "write_capacity": (
            "set_levels",
            {
                "absolute": ("aws_limit_value", 500),
                "percentage": {"warn": 70.0, "crit": 85.0},
            },
        ),
    }
