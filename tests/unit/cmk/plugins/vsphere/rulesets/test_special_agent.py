#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.vsphere.lib.special_agent import QueryType
from cmk.plugins.vsphere.rulesets.special_agent import rule_spec_special_agent_vsphere


@pytest.mark.parametrize(
    "partial_value",
    [
        pytest.param({"direct": True, "infos": []}, id="oldest format"),
        pytest.param({"direct": "vcenter", "infos": []}, id="old format"),
        pytest.param(
            {"direct": (QueryType.HOST_SYSTEM, ["hostsystem", "licenses"])}, id="new format"
        ),
    ],
)
def test_rule_spec_vsphere(partial_value: Mapping[str, object]) -> None:
    value = {
        "user": "foo",
        "secret": (
            "cmk_postprocessed",
            "explicit_password",
            ("uuid17ecd6df-0a04-4bf7-9d0a-40f3318f4d3a", "password"),
        ),
        "direct": True,
        "infos": [],
        "ssl": ("hostname", None),
        "skip_placeholder_vms": False,
        "snapshots_on_host": False,
        "spaces": "underscore",
        **partial_value,
    }
    valuespec = convert_to_legacy_rulespec(
        rule_spec_special_agent_vsphere, Edition.CRE, lambda x: x
    ).valuespec
    valuespec.validate_datatype(value, "")
    valuespec.validate_value(value, "")
