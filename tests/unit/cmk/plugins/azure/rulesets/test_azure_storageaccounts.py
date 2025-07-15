#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.ccc.version import Edition
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec
from cmk.plugins.azure.rulesets.azure_storageaccounts import (
    rule_spec_azure_storageaccounts_flow,
    rule_spec_azure_storageaccounts_performance,
    rule_spec_azure_storageaccounts_usage,
)
from cmk.rulesets.v1.rule_specs import CheckParameters


@pytest.mark.parametrize(
    ["rulespec", "rule"],
    [
        pytest.param(
            rule_spec_azure_storageaccounts_usage,
            {"used_capacity_levels": ("no_levels", None)},
            id="Usage: new param format",
        ),
        pytest.param(
            rule_spec_azure_storageaccounts_usage,
            {"used_capacity_levels": None},
            id="Usage: old param format",
        ),
        pytest.param(
            rule_spec_azure_storageaccounts_flow,
            {
                "transactions_levels": ("fixed", (1, 5)),
                "egress_levels": ("no_levels", None),
                "ingress_levels": ("fixed", (100 * 1024**2, 1024**3)),
            },
            id="Flow: new param format",
        ),
        pytest.param(
            rule_spec_azure_storageaccounts_flow,
            {
                "transactions_levels": (1, 5),
                "egress_levels": None,
                "ingress_levels": (100 * 1024**2, 1024**3),
            },
            id="Flow: old param format",
        ),
        pytest.param(
            rule_spec_azure_storageaccounts_performance,
            {
                "server_latency_levels": ("fixed", (1_000, 5_000)),
                "e2e_latency_levels": ("no_levels", None),
                "availability_levels": ("fixed", (75.0, 50.0)),
            },
            id="Perf: new param format",
        ),
        pytest.param(
            rule_spec_azure_storageaccounts_performance,
            {
                "server_latency_levels": (1_000, 5_000),
                "e2e_latency_levels": None,
                "availability_levels": (75.0, 50.0),
            },
            id="Perf: old param format",
        ),
    ],
)
def test_azure_storageaccounts_ruleset(rulespec: CheckParameters, rule: dict[str, object]) -> None:
    valuespec = convert_to_legacy_rulespec(rulespec, Edition.CRE, lambda x: x).valuespec
    valuespec.validate_datatype(rule, "")
    valuespec.validate_value(rule, "")
