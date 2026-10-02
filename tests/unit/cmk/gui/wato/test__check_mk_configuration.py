#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.wato._check_mk_configuration import (
    _migrate_piggybacked_host_files,
    Snmpv3Contexts,
)


@pytest.mark.parametrize(
    ("rule_value", "expected_result"),
    [
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [
                            ("exact_match", "some-host"),
                            ("regular_expression", "test.*"),
                        ],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [
                            ("exact_match", "some-host"),
                            ("regular_expression", "test.*"),
                        ],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            id="up-to-date format",
        ),
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "piggybacked_hostname_expressions": ["valid"],
                        "max_cache_age": "global",
                        "validity": {"period": 60, "check_mk_state": 0},
                    },
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [("exact_match", "valid")],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            id="legacy format with valid host name",
        ),
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "piggybacked_hostname_expressions": ["~test.*"],
                        "max_cache_age": "global",
                        "validity": {"period": 60, "check_mk_state": 0},
                    },
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [("regular_expression", "test.*")],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            id="legacy format with regular expression",
        ),
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "piggybacked_hostname_expressions": ["^test$", "^test2.*"],
                        "max_cache_age": "global",
                        "validity": {"period": 60, "check_mk_state": 0},
                    }
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [],
            },
            id="legacy format with invalid host names",
        ),
    ],
)
def test_migrate_piggybacked_host_files(
    rule_value: Mapping[str, object],
    expected_result: Mapping[str, object],
) -> None:
    assert _migrate_piggybacked_host_files(rule_value) == expected_result


@pytest.mark.parametrize(
    ("contexts", "expected_form_value"),
    [
        pytest.param(["vrf1", "mgmt"], [False, ["vrf1", "mgmt"]], id="without default context"),
        pytest.param(["vrf1", "", "mgmt"], [True, ["vrf1", "mgmt"]], id="with default context"),
    ],
)
def test_snmpv3_contexts_rule_maps_the_default_context_to_the_checkbox(
    contexts: list[str], expected_form_value: list[object]
) -> None:
    form_value = Snmpv3Contexts.valuespec.value_to_json((None, contexts, "stop_on_timeout"))

    assert form_value == [None, expected_form_value, "stop_on_timeout"]


def test_snmpv3_contexts_rule_keeps_existing_rules_without_default_context() -> None:
    rule_value = (None, ["vrf1", "mgmt"], "stop_on_timeout")

    assert Snmpv3Contexts.valuespec.transform_value(rule_value) == rule_value


def test_snmpv3_contexts_rule_moves_the_default_context_first() -> None:
    rule_value = Snmpv3Contexts.valuespec.transform_value(
        (None, ["vrf1", "", "mgmt"], "stop_on_timeout")
    )

    assert rule_value == (None, ["", "vrf1", "mgmt"], "stop_on_timeout")
