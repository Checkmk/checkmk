#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.plugins.wato.check_parameters.lvm_lvs_pools import rule_spec_lvm_lvs_pools
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(
            {},
            id="empty",
        ),
        pytest.param(
            {"levels_meta": (80.0, 90.0), "levels_data": (80.0, 90.0)},
            id="pre v1 API all fields",
        ),
        pytest.param(
            {"levels_data": (80.0, 90.0)},
            id="pre v1 API only data",
        ),
        pytest.param(
            {},
            id="pre v1 API empty",
        ),
    ],
)
def test_rule_spec_lvm_lvs_pools(rule: dict[str, object]) -> None:
    validating_rule_spec = convert_to_legacy_rulespec(
        rule_spec_lvm_lvs_pools, Edition.CRE, lambda x: x
    )
    validating_rule_spec.valuespec.validate_datatype(rule, "")
    validating_rule_spec.valuespec.validate_value(rule, "")
