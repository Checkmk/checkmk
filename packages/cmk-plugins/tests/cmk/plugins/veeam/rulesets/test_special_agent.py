#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.veeam.rulesets.special_agent import rule_spec_special_agent_veeam
from cmk.plugins.veeam.server_side_calls.special_agent import Params
from cmk.plugins.veeam.special_agent.agent_veeam import SECTIONS
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    DefaultValue,
    Integer,
    MultipleChoice,
    validators,
)
from cmk.server_side_calls.v1 import Secret

BASE_PARAMS = {
    "connection": ("ip_address", None),
    "port": 9419,
    "user": "monitoring",
    "password": Secret(1),
    "disable_cert_verification": False,
    "sections": ["veeam_backup_jobs"],
}

# A stored value for every choice the ruleset offers. Adding a choice to the
# ruleset without adding it here fails the test, so the server-side call can't
# silently fall behind.
CHOICE_VALUES: Mapping[str, Mapping[str, object]] = {
    "connection": {
        "ip_address": None,
        "host_name": None,
        "custom_address": "backup.example.com",
    },
}


def _choice_names(element: str) -> set[str]:
    form = rule_spec_special_agent_veeam.parameter_form().elements[element].parameter_form
    assert isinstance(form, CascadingSingleChoice)
    return {choice.name for choice in form.elements}


@pytest.mark.parametrize("element", sorted(CHOICE_VALUES))
def test_every_choice_is_accepted_by_the_server_side_call(element: str) -> None:
    values = CHOICE_VALUES[element]
    assert _choice_names(element) == set(values)

    for name, value in values.items():
        Params.model_validate({**BASE_PARAMS, element: (name, value)})


def test_the_port_is_prefilled_with_the_veeam_default() -> None:
    port_form = rule_spec_special_agent_veeam.parameter_form().elements["port"].parameter_form
    assert isinstance(port_form, Integer)

    assert port_form.prefill == DefaultValue(9419)


def _sections_form() -> MultipleChoice:
    form = rule_spec_special_agent_veeam.parameter_form().elements["sections"].parameter_form
    assert isinstance(form, MultipleChoice)
    return form


def test_all_sections_are_selected_by_default() -> None:
    form = _sections_form()
    all_names = [element.name for element in form.elements]

    assert form.prefill == DefaultValue(all_names)
    # the default selection is accepted by the server-side call
    Params.model_validate({**BASE_PARAMS, "sections": all_names})


def test_section_choices_match_the_agent_registry() -> None:
    # The ruleset choices and the agent's SECTIONS are hand-maintained in lockstep:
    # a choice the agent does not know is rejected at the CLI (and terminates the
    # agent for everyone who has it selected), and a section not offered as a choice
    # can never be fetched. Keep them equal.
    choices = {element.name for element in _sections_form().elements}

    assert choices == {name for name, _ in SECTIONS}


def test_at_least_one_section_must_be_selected() -> None:
    custom_validate = _sections_form().custom_validate
    assert custom_validate is not None
    (validate,) = custom_validate

    with pytest.raises(validators.ValidationError):
        validate([])
