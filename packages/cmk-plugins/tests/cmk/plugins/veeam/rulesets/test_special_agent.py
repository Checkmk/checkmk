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
    DictElement,
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
    "additional_sections": [],
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

    assert port_form.prefill == DefaultValue(443)


def _multiple_choice(element: str) -> MultipleChoice:
    form = rule_spec_special_agent_veeam.parameter_form().elements[element].parameter_form
    assert isinstance(form, MultipleChoice)
    return form


def _choice_names_of(element: str) -> list[str]:
    return [choice.name for choice in _multiple_choice(element).elements]


def test_only_the_services_a_viewer_may_read_are_selected_by_default() -> None:
    assert _multiple_choice("sections").prefill == DefaultValue(_choice_names_of("sections"))
    assert _multiple_choice("additional_sections").prefill == DefaultValue([])


def test_section_choices_match_the_agent_registry() -> None:
    # The ruleset choices and the agent's SECTIONS are hand-maintained in lockstep:
    # a choice the agent does not know is rejected at the CLI (and terminates the
    # agent for everyone who has it selected), and a section not offered as a choice
    # can never be fetched. Keep them equal.
    viewer = set(_choice_names_of("sections"))
    additional = set(_choice_names_of("additional_sections"))

    assert not viewer & additional
    assert viewer | additional == {name for name, _ in SECTIONS}


def _validate_rule(value: Mapping[str, object]) -> None:
    custom_validate = rule_spec_special_agent_veeam.parameter_form().custom_validate
    assert custom_validate is not None
    for validate in custom_validate:
        validate(value)


def test_at_least_one_section_must_be_selected() -> None:
    with pytest.raises(validators.ValidationError):
        _validate_rule({**BASE_PARAMS, "sections": [], "additional_sections": []})


def test_selecting_only_additional_sections_is_valid() -> None:
    _validate_rule({**BASE_PARAMS, "sections": [], "additional_sections": ["veeam_license"]})


def _timeout_element() -> DictElement[int]:
    element = rule_spec_special_agent_veeam.parameter_form().elements["timeout"]
    assert isinstance(element.parameter_form, Integer)
    return element


def test_the_timeout_is_optional() -> None:
    assert not _timeout_element().required
    assert Params.model_validate(BASE_PARAMS).timeout is None


def test_timeouts_below_one_second_are_rejected() -> None:
    custom_validate = _timeout_element().parameter_form.custom_validate
    assert custom_validate is not None
    (validate,) = custom_validate

    validate(1)
    with pytest.raises(validators.ValidationError):
        validate(0)
