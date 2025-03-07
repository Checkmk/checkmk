#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.tcp.rulesets.tcp_connections import rule_spec_tcp_connections
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel


@pytest.mark.parametrize(
    "max_states",
    [
        pytest.param(("fixed", (100, 500)), id="new format"),
        pytest.param((100, 500), id="old format"),
    ],
)
def test_rule_spec_tcp_connections(
    max_states: tuple[int, int] | SimpleLevelsConfigModel,
) -> None:
    rule = {
        "proto": "TCP",
        "state": "LISTENING",
        "local_ip": "127.0.0.1",
        "local_port": 22,
        "remote_ip": "127.0.0.1",
        "remote_port": 22,
        "max_states": max_states,
        "min_states": ("no_levels", None),
    }
    value = ("netstat", "foobar", rule)

    valuespec = convert_to_legacy_rulespec(
        rule_spec_tcp_connections, Edition.CRE, lambda x: x
    ).valuespec

    # FYI: We want to test the validation of the specific rule content, not the generic check-plugin
    # selection. Hence, we inject the dict of possible elements.
    valuespec._elements[0].get_elements = lambda: {"netstat": None}  # type: ignore[attr-defined]

    valuespec.validate_datatype(value, "")
    valuespec.validate_value(value, "")
