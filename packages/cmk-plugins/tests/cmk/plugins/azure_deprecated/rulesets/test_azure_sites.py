#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.azure_deprecated.rulesets.azure_sites import (
    rule_spec_azure_sites,
)


def _migrate(params: object) -> Mapping[str, object]:
    migrate = rule_spec_azure_sites.parameter_form().migrate
    assert migrate is not None, "rule_spec_azure_sites has no migrate wired"
    return migrate(params)


@pytest.mark.parametrize(
    ["params", "expected"],
    [
        pytest.param(
            {"avg_response_time_levels": (1.0, 10.0)},
            {"avg_response_time_levels": ("fixed", (1.0, 10.0))},
            id="legacy-avg-response-time",
        ),
        pytest.param(
            {"error_rate_levels": (0.01, 0.04)},
            {"error_rate_levels": ("fixed", (0.01, 0.04))},
            id="legacy-error-rate",
        ),
        pytest.param(
            {"cpu_time_percent_levels": (85.0, 95.0)},
            {"cpu_time_percent_levels": ("fixed", (85.0, 95.0))},
            id="legacy-cpu-time-percent",
        ),
        pytest.param(
            {
                "avg_response_time_levels": (1.0, 10.0),
                "error_rate_levels": (0.01, 0.04),
                "cpu_time_percent_levels": (85.0, 95.0),
            },
            {
                "avg_response_time_levels": ("fixed", (1.0, 10.0)),
                "error_rate_levels": ("fixed", (0.01, 0.04)),
                "cpu_time_percent_levels": ("fixed", (85.0, 95.0)),
            },
            id="legacy-all-levels",
        ),
    ],
)
def test_migrate_params_legacy_levels(
    params: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    assert _migrate(params) == expected


def test_migrate_params_already_migrated() -> None:
    params = {
        "avg_response_time_levels": ("fixed", (1.0, 10.0)),
        "error_rate_levels": ("fixed", (0.01, 0.04)),
        "cpu_time_percent_levels": ("fixed", (85.0, 95.0)),
    }
    assert _migrate(params) == params


def test_migrate_params_empty_dict() -> None:
    assert _migrate({}) == {}


def test_migrate_params_non_dict() -> None:
    assert _migrate(None) == {}
