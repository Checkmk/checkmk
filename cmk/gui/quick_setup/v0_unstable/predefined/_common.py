#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Any, Mapping, Sequence

from cmk.utils.hostaddress import HostName

from cmk.automations.results import DiagSpecialAgentHostConfig, DiagSpecialAgentInput

from cmk.checkengine.discovery import CheckPreviewEntry

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.visitors import DataOrigin
from cmk.gui.form_specs.vue.visitors._registry import form_spec_registry
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData, ServiceInterest
from cmk.gui.watolib.passwords import load_passwords

from cmk.rulesets.v1.form_specs import Dictionary, Password


def _collect_params_with_defaults_from_form_data(
    all_stages_form_data: ParsedFormData, rulespec_name: str
) -> Mapping[str, object]:
    return _add_defaults_to_form_data(
        _get_rule_defaults(rulespec_name),
        _collect_params_from_form_data(all_stages_form_data, rulespec_name),
    )


def _collect_passwords_from_form_data(
    all_stages_form_data: ParsedFormData, rulespec_name: str
) -> Mapping[str, str]:
    if (parameter_form := _get_parameter_form_from_rulespec_name(rulespec_name)) is None:
        return {}
    possible_expected_password_keys = [
        key
        for key in parameter_form.elements.keys()
        if isinstance(parameter_form.elements[key].parameter_form, Password)
    ]

    return {
        form_spec_value[2][0]: (
            form_spec_value[2][1]
            if form_spec_value[1] == "explicit_password"
            else load_passwords()[form_spec_value[2][1]]
        )
        for form_data in all_stages_form_data.values()
        if isinstance(form_data, dict)
        for form_spec_id, form_spec_value in form_data.items()
        if form_spec_id in possible_expected_password_keys
        if form_spec_value[0] == "cmk_postprocessed"
    }


def _create_diag_special_agent_input(
    rulespec_name: str,
    host_name: str | None,
    passwords: Mapping[str, str],
    params: Mapping[str, object],
) -> DiagSpecialAgentInput:
    return DiagSpecialAgentInput(
        host_config=DiagSpecialAgentHostConfig(
            host_name=HostName(host_name or ""), host_alias=host_name or ""
        ),
        agent_name=rulespec_name.split(":")[1],
        params=params,
        passwords=passwords,
    )


def _find_unique_id(form_data: Any, target_key: str) -> None | str:
    if isinstance(form_data, dict):
        for key, value in form_data.items():
            if key == target_key:
                return value
            result = _find_unique_id(value, target_key)
            if result is not None:
                return result
        return None
    if isinstance(form_data, list):
        for item in form_data:
            result = _find_unique_id(item, target_key)
            if result is not None:
                return result
    return None


def _add_defaults_to_form_data(
    default_dict: dict, update_dict: Mapping[str, object]
) -> Mapping[str, object]:
    return {
        **{
            key: (
                _add_defaults_to_form_data(default_dict[key], value)
                if isinstance(value, dict)
                and key in default_dict
                and isinstance(default_dict[key], dict)
                else value
            )
            for key, value in update_dict.items()
        },
        **{key: value for key, value in default_dict.items() if key not in update_dict},
    }


def _get_parameter_form_from_rulespec_name(rulespec_name: str) -> Dictionary | None:
    _parameter_form = form_spec_registry[rulespec_name.split(":")[1]].rule_spec.parameter_form
    return _parameter_form() if callable(_parameter_form) else _parameter_form


def _collect_params_from_form_data(
    all_stages_form_data: ParsedFormData, rulespec_name: str
) -> Mapping[str, object]:
    if (parameter_form := _get_parameter_form_from_rulespec_name(rulespec_name)) is None:
        return {}
    possible_expected_keys = parameter_form.elements.keys()

    return {
        form_spec_id: form_spec_value
        for form_data in all_stages_form_data.values()
        if isinstance(form_data, dict)
        for form_spec_id, form_spec_value in form_data.items()
        if form_spec_id in possible_expected_keys
    }


def _get_rule_defaults(rulespec_name: str) -> dict[str, object]:
    if (parameter_form := _get_parameter_form_from_rulespec_name(rulespec_name)) is None:
        return {}

    return serialize_data_for_frontend(
        form_spec=parameter_form,
        field_id="rule_id",
        origin=DataOrigin.DISK,
        do_validate=False,
    ).data


def _match_service_interest(
    check_preview_entry: CheckPreviewEntry, services_of_interest: Sequence[ServiceInterest]
) -> ServiceInterest | None:
    for service_of_interest in services_of_interest:
        # TODO: decide if we want to match on all of services_of_interest (and yield the service
        #  interests) or just the first one just like now.
        if re.match(
            service_of_interest.check_plugin_name_pattern, check_preview_entry.check_plugin_name
        ):
            return service_of_interest
    return None
