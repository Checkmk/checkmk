#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.cadvisor_cpu import (
    check_cadvisor_cpu,
    discover_cadvisor_cpu,
    parse_cadvisor_cpu,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{"cpu_user": [{"value": "0.10996819381471273", "labels": {"name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5"}, "host_selection_label": "name"}], "cpu_system": [{"value": "0.12688637747851422", "labels": {"name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5"}, "host_selection_label": "name"}]}'
                ]
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_cadvisor_cpu(
    string_table: StringTable, expected_discoveries: Sequence[tuple[None, dict[str, Any]]]
) -> None:
    """Test discovery function for cadvisor_cpu check."""
    parsed = parse_cadvisor_cpu(string_table)
    result = list(discover_cadvisor_cpu(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                [
                    '{"cpu_user": [{"value": "0.10996819381471273", "labels": {"name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5"}, "host_selection_label": "name"}], "cpu_system": [{"value": "0.12688637747851422", "labels": {"name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5"}, "host_selection_label": "name"}]}'
                ]
            ],
            [
                (0, "User: 0.11%", [("user", 0.10996819381471273, None, None)]),
                (0, "System: 0.13%", [("system", 0.12688637747851422, None, None)]),
                (0, "Total CPU: 0.24%", [("util", 0.23685457129322696, None, None)]),
            ],
        ),
    ],
)
def test_check_cadvisor_cpu(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for cadvisor_cpu check."""
    parsed = parse_cadvisor_cpu(string_table)
    result = list(check_cadvisor_cpu(item, params, parsed))
    assert result == expected_results
