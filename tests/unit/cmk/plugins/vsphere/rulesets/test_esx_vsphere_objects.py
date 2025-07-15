#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.vsphere.rulesets.esx_vsphere_objects import (
    rule_spec_esx_vsphere_objects,
    rule_spec_esx_vsphere_objects_discovery,
)
from cmk.rulesets.v1.form_specs import ServiceState


@pytest.mark.parametrize(
    "partial_value",
    [
        pytest.param({}),
        pytest.param({"standBy": ServiceState.WARN}),
        pytest.param({"poweredOff": ServiceState.CRIT}),
    ],
)
def test_check_rulespec(partial_value: Mapping[str, int]) -> None:
    value = {
        "states": {
            "standBy": ServiceState.WARN,
            "poweredOff": ServiceState.WARN,
            "poweredOn": ServiceState.OK,
            "suspended": ServiceState.WARN,
            "unknown": ServiceState.UNKNOWN,
        }
    }
    value["states"].update(partial_value)

    valuespec = convert_to_legacy_rulespec(
        rule_spec_esx_vsphere_objects, Edition.CRE, lambda x: x
    ).valuespec
    valuespec.validate_datatype(value, "")
    valuespec.validate_value(value, "")


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"templates": True}),
        pytest.param({"templates": False}),
    ],
)
def test_discovery_rulespec(params: Mapping[str, bool]) -> None:
    valuespec = convert_to_legacy_rulespec(
        rule_spec_esx_vsphere_objects_discovery, Edition.CRE, lambda x: x
    ).valuespec
    valuespec.validate_datatype(params, "")
    valuespec.validate_value(params, "")
