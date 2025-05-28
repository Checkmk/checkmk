#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, cast

from cmk.ccc.hostaddress import HostName

from cmk.automations.results import DiagSpecialAgentHostConfig, DiagSpecialAgentInput

from cmk.checkengine.discovery import CheckPreviewEntry

from cmk.gui.form_specs.vue.form_spec_visitor import (
    serialize_data_for_frontend,
    transform_to_disk_model,
)
from cmk.gui.form_specs.vue.visitors import DataOrigin
from cmk.gui.form_specs.vue.visitors._type_defs import DiskModel
from cmk.gui.quick_setup.private.widgets import ConditionalNotificationStageWidget
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupStage
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData, ServiceInterest
from cmk.gui.quick_setup.v0_unstable.widgets import (
    Collapsible,
    FormSpecId,
    FormSpecWrapper,
    ListOfWidgets,
    Widget,
)
from cmk.gui.watolib.passwords import load_passwords

from cmk.rulesets.v1.form_specs import Dictionary, FormSpec, Password


def _collect_params_with_defaults_from_form_data(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    return _add_defaults_to_form_data(
        _get_rule_defaults(parameter_form),
        _collect_params_from_form_data(all_stages_form_data, parameter_form),
    )


def _collect_passwords_from_form_data(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, str]:
    possible_expected_password_keys = [
        key
        for key in parameter_form.elements.keys()
        if isinstance(parameter_form.elements[key].parameter_form, Password)
    ]

    return {
        form_spec_value[2][0]: (
            form_spec_value[2][1]
            if form_spec_value[1] == "explicit_password"
            else load_passwords()[form_spec_value[2][0]]["password"]
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


def _find_id_in_form_data(form_data: Any, target_key: str) -> None | str:
    if isinstance(form_data, dict):
        for key, value in form_data.items():
            if key == target_key:
                assert isinstance(value, str)
                return value
            result = _find_id_in_form_data(value, target_key)
            if result is not None:
                return result
        return None
    if isinstance(form_data, list):
        for item in form_data:
            result = _find_id_in_form_data(item, target_key)
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


def _collect_params_from_form_data(
    all_stages_form_data: ParsedFormData,
    parameter_form: Dictionary,
) -> Mapping[str, object]:
    possible_expected_keys = parameter_form.elements.keys()

    return {
        form_spec_id: form_spec_value
        for form_data in all_stages_form_data.values()
        if isinstance(form_data, dict)
        for form_spec_id, form_spec_value in form_data.items()
        if form_spec_id in possible_expected_keys
    }


def _get_rule_defaults(parameter_form: Dictionary) -> DiskModel:
    # We need to create a valid default ruleset configuration that adheres to the form spec.
    # This two-step process:
    # 1.  First serialize the form to the frontend format, which automatically fills in
    #     any missing values with appropriate defaults (including fallback values for invalid entries)
    # 1a. Invalid entries exist since we have required dictelements without a DefaultValue prefill
    # 2.  Then convert this valid structure back to disk format so it can be properly merged
    #     with the actual configuration data from the quick setup stages
    return transform_to_disk_model(
        parameter_form,
        serialize_data_for_frontend(
            form_spec=parameter_form,
            field_id="rule_id",
            origin=DataOrigin.DISK,
            do_validate=False,
        ).data,
    )


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


def stage_components(stage: QuickSetupStage) -> Sequence[Widget]:
    return (
        stage.configure_components()
        if callable(stage.configure_components)
        else stage.configure_components
    )


def _flatten_formspec_wrappers(components: Sequence[Widget]) -> Iterator[FormSpecWrapper]:
    for component in components:
        if isinstance(component, ListOfWidgets | Collapsible | ConditionalNotificationStageWidget):
            yield from iter(_flatten_formspec_wrappers(component.items))

        if isinstance(component, FormSpecWrapper):
            yield component


def build_formspec_map_from_stages(
    stages: Sequence[QuickSetupStage],
) -> Mapping[FormSpecId, FormSpec]:
    return {
        widget.id: cast(FormSpec, widget.form_spec)
        for stage in stages
        for widget in _flatten_formspec_wrappers(stage_components(stage))
    }
