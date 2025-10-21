#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disable-error-code="type-arg"
from typing import Any

from cmk.gui.form_specs.unstable import TimeSpecific
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.inventory import RulespecGroupInventory
from cmk.gui.plugins.wato.utils import RulespecGroupCheckParametersDiscovery
from cmk.gui.valuespec import Dictionary, Migrate, Transform, ValueSpec
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    FormSpecNotImplementedError,
    rulespec_registry,
    TimeperiodValuespec,
)
from cmk.rulesets.v1.form_specs import Dictionary as FSDictionary
from cmk.rulesets.v1.form_specs import FormSpec

_KNOWN_OFFENDERS = {
    "inv_retention_intervals",
}


def _get_first_actual_valuespec(vspec: ValueSpec) -> ValueSpec:
    if isinstance(vspec, TimeperiodValuespec):
        return _get_first_actual_valuespec(vspec._enclosed_valuespec)
    if isinstance(vspec, Transform | Migrate):
        return _get_first_actual_valuespec(vspec._valuespec)
    return vspec


def _get_first_actual_form_spec(form_spec: FormSpec[Any]) -> FormSpec[Any]:
    if isinstance(form_spec, TransformDataForLegacyFormatOrRecomposeFunction):
        return _get_first_actual_form_spec(form_spec.wrapped_form_spec)
    if isinstance(form_spec, TimeSpecific):
        return _get_first_actual_form_spec(form_spec.parameter_form)
    return form_spec


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

        try:
            if isinstance(_get_first_actual_form_spec(element.form_spec), FSDictionary):
                continue
        except FormSpecNotImplementedError:
            if isinstance(_get_first_actual_valuespec(element.valuespec), Dictionary):
                continue

        findings.add(element.name)

    assert findings == _KNOWN_OFFENDERS
