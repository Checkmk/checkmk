#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.inventory import RulespecGroupInventory
from cmk.gui.plugins.wato.utils import RulespecGroupCheckParametersDiscovery
from cmk.gui.valuespec import Dictionary, Migrate, Transform, ValueSpec
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    TimeperiodValuespec,
)

_KNOWN_OFFENDERS = {
    "inv_retention_intervals",
}


def _get_first_actual_valuespec(vspec: ValueSpec) -> ValueSpec:
    if isinstance(vspec, Transform | Migrate):
        return _get_first_actual_valuespec(vspec._valuespec)
    return vspec


def test_plugin_parameters_are_dict() -> None:
    findings = set()
    for element in rulespec_registry.values():
        if not (
            element.group in {RulespecGroupCheckParametersDiscovery, RulespecGroupInventory}
            or isinstance(
                element, CheckParameterRulespecWithItem | CheckParameterRulespecWithoutItem
            )
        ):
            continue

        vspec = element._valuespec()
        if isinstance(vspec, TimeperiodValuespec):
            vspec = vspec._enclosed_valuespec

        if isinstance(_get_first_actual_valuespec(vspec), Dictionary):
            continue

        findings.add(element.name)

    assert findings == _KNOWN_OFFENDERS
