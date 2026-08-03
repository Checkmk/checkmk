#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""Shared test data for test_openapi_host_config edition-specific tests."""

from typing import Any

import pytest

VALID_METRICS_ASSOCIATION_CONFIG: dict[str, Any] = {
    "host_name_lookup_rules": [
        {
            "resource_attributes": [{"key": "k", "value": "v"}],
            "scope_attributes": [],
            "data_point_attributes": [],
        },
    ],
}

INVALID_METRICS_ASSOCIATION_PARAMS = [
    pytest.param(
        "not-a-list-or-tuple",
        "Input should be a valid tuple",
        id="top_level_type_mismatch",
    ),
    pytest.param(["enabled"], "Field required", id="tuple_length_too_short"),
    pytest.param(
        ["enabled", VALID_METRICS_ASSOCIATION_CONFIG, "extra-item"],
        "Tuple should have at most 2 items after validation",
        id="tuple_length_too_long",
    ),
    pytest.param(
        ["invalid_status", VALID_METRICS_ASSOCIATION_CONFIG],
        "Input should be 'enabled'",
        id="status_enum_violation",
    ),
    pytest.param(
        ["enabled", "this-should-be-a-dict-or-none"],
        "Input should be a dictionary or an instance of MetricsAssociationEnabledModel",
        id="config_type_mismatch",
    ),
    pytest.param(
        [
            "enabled",
            {
                # Missing 'host_name_lookup_rules'
            },
        ],
        "Field required",
        id="missing_required_config_key",
    ),
    pytest.param(
        [
            "enabled",
            {
                "host_name_lookup_rules": "not-a-list",  # Wrong type
            },
        ],
        "instances are not allowed as a Sequence value",
        id="lookup_rules_type_mismatch",
    ),
    pytest.param(
        [
            "enabled",
            {
                "host_name_lookup_rules": [],  # An enabled association needs at least one rule
            },
        ],
        "at least 1 item",
        id="lookup_rules_empty",
    ),
    pytest.param(
        [
            "enabled",
            {
                "host_name_lookup_rules": [
                    {
                        # Missing 'data_point_attributes'
                        "resource_attributes": [{"key": "k", "value": "v"}],
                        "scope_attributes": [],
                    },
                ],
            },
        ],
        "Field required",
        id="rule_missing_key",
    ),
    pytest.param(
        [
            "enabled",
            {
                "host_name_lookup_rules": [
                    {
                        "resource_attributes": [{"key": "k", "value": "v"}],
                        "scope_attributes": [
                            {
                                "key": "k",
                                # Missing 'value' key
                            }
                        ],
                        "data_point_attributes": [],
                    },
                ],
            },
        ],
        "Field required",
        id="filter_item_missing_key",
    ),
]
