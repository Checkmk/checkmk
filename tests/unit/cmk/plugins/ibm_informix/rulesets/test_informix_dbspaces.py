#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec
from cmk.plugins.ibm_informix.rulesets.informix_dbspaces import rule_spec_informix_dbspaces


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param({"levels": (1, 1000)}, id="pre-migration levels"),
        pytest.param({"levels": ("fixed", (1, 1000))}, id="levels"),
        pytest.param({"levels_perc": None}, id="pre-migration levels_perc"),
        pytest.param({"levels_perc": ("no_levels", None)}, id="levels_perc"),
    ],
)
def test_rule_spec_informix_dbspaces(rule: dict[str, object]) -> None:
    valuespec = convert_to_legacy_rulespec(
        rule_spec_informix_dbspaces, Edition.CRE, lambda x: x
    ).valuespec

    valuespec.validate_datatype(rule, "")
    valuespec.validate_value(rule, "")
