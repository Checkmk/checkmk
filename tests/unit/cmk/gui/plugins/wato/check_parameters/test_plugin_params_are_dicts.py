#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.unit.cmk.conftest import import_plugins

from cmk.gui.inventory import RulespecGroupInventory
from cmk.gui.plugins.wato.utils import RulespecGroupCheckParametersDiscovery
from cmk.gui.valuespec import Dictionary, Transform
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    TimeperiodValuespec,
)

_KNOWN_OFFENDERS = {
    "inv_retention_intervals",
}


@import_plugins(["cmk.gui.cce.plugins.wato"])
def test_plugin_parameters_are_dict() -> None:
    findings = set()
    for element in rulespec_registry.values():
        if not (
            element.group == RulespecGroupCheckParametersDiscovery
            or element.group == RulespecGroupInventory
            or isinstance(
                element,
                (CheckParameterRulespecWithItem, CheckParameterRulespecWithoutItem),
            )
        ):
            continue

        vspec = element._valuespec()
        if isinstance(vspec, TimeperiodValuespec):
            vspec = vspec._enclosed_valuespec

        if isinstance(vspec, Dictionary):
            continue
        if isinstance(vspec, Transform) and isinstance(vspec._valuespec, Dictionary):
            continue

        findings.add(element.name)

    assert findings == _KNOWN_OFFENDERS
