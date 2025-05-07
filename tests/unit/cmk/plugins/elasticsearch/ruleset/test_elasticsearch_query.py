#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.elasticsearch.rulesets.elasticsearch_query import _migrate

EXAMPLE_CHECK_CONFIG_LATEST = {
    "svc_item": "suffix",
    "hostname": "127.0.0.1",
    "user": "username",
    "password": (
        "cmk_postprocessed",
        "explicit_password",
        ("uuidc7c07295-baf6-4261-a003-3d9734de3f61", "password"),
    ),
    "protocol": "https",
    "verify_tls_cert": True,
    "port": 9200,
    "pattern": ".*",
    "index": ["index_to_query", "second_index_to_query"],
    "fieldname": ["field_to_query", "second_field_to_query"],
    "timerange": 3660.0,
    "upper_log_count_thresholds": ("fixed", (10, 20)),
    "lower_log_count_thresholds": ("fixed", (2, 1)),
    "condition": {},
    "options": {"disabled": False, "description": "test"},
}

EXAMPLE_CHECK_CONFIG_2_4 = {
    "svc_item": "suffix",
    "hostname": "127.0.0.1",
    "user": "username",
    "password": (
        "cmk_postprocessed",
        "explicit_password",
        ("uuidc7c07295-baf6-4261-a003-3d9734de3f61", "password"),
    ),
    "protocol": "https",
    "port": 9200,
    "pattern": ".*",
    "index": ["index_to_query", "second_index_to_query"],
    "fieldname": ["field_to_query", "second_field_to_query"],
    "timerange": 3660.0,
    "count": ("fixed", (10, 20)),
    "condition": {},
    "options": {"disabled": False, "description": "test"},
}

EXPECTED_CONFIG_FROM_2_4 = {
    "svc_item": "suffix",
    "hostname": "127.0.0.1",
    "user": "username",
    "password": (
        "cmk_postprocessed",
        "explicit_password",
        ("uuidc7c07295-baf6-4261-a003-3d9734de3f61", "password"),
    ),
    "protocol": "https",
    "port": 9200,
    "pattern": ".*",
    "index": ["index_to_query", "second_index_to_query"],
    "fieldname": ["field_to_query", "second_field_to_query"],
    "timerange": 3660.0,
    "upper_log_count_thresholds": ("fixed", (10, 20)),
    "verify_tls_cert": True,
    "condition": {},
    "options": {"disabled": False, "description": "test"},
}


def test_migrate_from_2_4() -> None:
    assert _migrate(EXAMPLE_CHECK_CONFIG_2_4) == EXPECTED_CONFIG_FROM_2_4


def test_migrate_does_not_modify_current() -> None:
    expected_config = EXAMPLE_CHECK_CONFIG_LATEST.copy()
    assert _migrate(EXAMPLE_CHECK_CONFIG_LATEST) == expected_config
