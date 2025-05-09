#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.haproxy.rulesets.haproxy import (
    rule_spec_haproxy_frontend,
    rule_spec_haproxy_server,
)


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"OPEN": 1},
        {"STOP": 0},
        {"OPEN": 0, "STOP": 0},
    ],
)
def test_rulesepc_frontend(value: Mapping[str, int]) -> None:
    valuespec = convert_to_legacy_rulespec(
        rule_spec_haproxy_frontend, Edition.CRE, lambda x: x
    ).valuespec
    valuespec.validate_datatype(value, "")
    valuespec.validate_value(value, "")


@pytest.mark.parametrize(
    "value", [{}, {"UP": 0}, {"UP": 1, "MAINT": 0}, {"MAINT (resolution)": 1}, {"MAINT_RES": 1}]
)
def test_rulespec_server(value: Mapping[str, int]) -> None:
    valuespec = convert_to_legacy_rulespec(
        rule_spec_haproxy_server, Edition.CRE, lambda x: x
    ).valuespec
    valuespec.validate_datatype(value, "")
    valuespec.validate_value(value, "")
