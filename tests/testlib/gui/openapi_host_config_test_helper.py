#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared test data for test_openapi_host_config edition-specific tests."""

from typing import Any

import pytest

VALID_METRICS_ASSOCIATION_CONFIG: dict[str, Any] = {
    "attribute_filters": [],
    "host_name_resource_attribute_key": "service.name",
}

INVALID_METRICS_ASSOCIATION_PARAMS = [
    pytest.param(
        "not-a-list-or-tuple",
        "Not a valid tuple.",
        id="top_level_type_mismatch",
    ),
    pytest.param(["enabled"], "Length must be 2", id="tuple_length_too_short"),
    pytest.param(
        ["enabled", VALID_METRICS_ASSOCIATION_CONFIG, "extra-item"],
        "Length must be 2",
        id="tuple_length_too_long",
    ),
    pytest.param(
        ["invalid_status", VALID_METRICS_ASSOCIATION_CONFIG],
        "is not one of the enum values: ['enabled', 'disabled']",
        id="status_enum_violation",
    ),
    pytest.param(
        ["enabled", "this-should-be-a-dict-or-none"],
        "Invalid input type",
        id="config_type_mismatch",
    ),
    pytest.param(
        [
            "enabled",
            {
                # Missing 'host_name_resource_attribute_key'
                "attribute_filters": {}
            },
        ],
        "Missing data for required field",
        id="missing_required_config_key",
    ),
    pytest.param(
        [
            "enabled",
            {
                "host_name_resource_attribute_key": "service.name",
                "attribute_filters": "not-a-dict",  # Wrong type
            },
        ],
        "Invalid input type",
        id="filters_type_mismatch",
    ),
    pytest.param(
        [
            "enabled",
            {
                "host_name_resource_attribute_key": "service.name",
                "attribute_filters": {
                    # Missing 'data_point_attributes'
                    "resource_attributes": [{"key": "k", "value": "v"}],
                    "scope_attributes": [],
                },
            },
        ],
        "Missing data for required field",
        id="filters_missing_key",
    ),
    pytest.param(
        [
            "enabled",
            {
                "host_name_resource_attribute_key": "service.name",
                "attribute_filters": {
                    "resource_attributes": [{"key": "k", "value": "v"}],
                    "scope_attributes": [
                        {
                            "key": "k",
                            # Missing 'value' key
                        }
                    ],
                    "data_point_attributes": [],
                },
            },
        ],
        "Missing data for required field",
        id="filter_item_missing_key",
    ),
]
