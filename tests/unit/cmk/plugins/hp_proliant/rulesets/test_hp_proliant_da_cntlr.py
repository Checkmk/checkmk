#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.version import Edition
from cmk.gui.rule_specs.legacy_converter import convert_to_legacy_rulespec
from cmk.plugins.hp_proliant.agent_based.hp_proliant_da_cntlr import DEFAULT_PARAMETERS
from cmk.plugins.hp_proliant.rulesets.hp_proliant_da_cntlr import rule_spec_hp_proliant_da_cntlr
from cmk.rulesets.v1.form_specs import Dictionary, FormSpec, ServiceState


def test_check_default_parameters_are_valid() -> None:
    valuespec = convert_to_legacy_rulespec(
        rule_spec_hp_proliant_da_cntlr, Edition.COMMUNITY, lambda x: x
    ).valuespec

    valuespec.validate_datatype(dict(DEFAULT_PARAMETERS), "")
    valuespec.validate_value(dict(DEFAULT_PARAMETERS), "")


def test_form_prefills_match_check_default_parameters() -> None:
    form = rule_spec_hp_proliant_da_cntlr.parameter_form()

    prefills = {
        field: _state_prefills(element.parameter_form) for field, element in form.elements.items()
    }

    assert prefills == DEFAULT_PARAMETERS


def _state_prefills(form: FormSpec[object]) -> dict[str, int]:
    assert isinstance(form, Dictionary)
    prefills: dict[str, int] = {}
    for value, element in form.elements.items():
        assert isinstance(element.parameter_form, ServiceState)
        prefills[value] = element.parameter_form.prefill.value
    return prefills
