#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator, Mapping, MutableMapping, MutableSequence, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, cast

from cmk.utils.hostaddress import HostName

from cmk.automations.results import (
    DiagSpecialAgentHostConfig,
    DiagSpecialAgentInput,
    SpecialAgentDiscoveryPreviewResult,
)

from cmk.checkengine.discovery import CheckPreviewEntry

from cmk.gui.form_specs.vue.form_spec_visitor import (
    parse_value_from_frontend,
    serialize_data_for_frontend,
    validate_value_from_frontend,
)
from cmk.gui.form_specs.vue.visitors._registry import form_spec_registry
from cmk.gui.form_specs.vue.visitors._type_defs import DataOrigin
from cmk.gui.quick_setup.v0_unstable.definitions import IncomingStage, QuickSetupSaveRedirect
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetup, QuickSetupStage
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
    RawFormData,
    ServiceInterest,
)
from cmk.gui.quick_setup.v0_unstable.widgets import (
    Collapsible,
    FormSpecId,
    FormSpecWrapper,
    ListOfWidgets,
    Widget,
)
from cmk.gui.watolib.passwords import load_passwords

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import Dictionary, FormSpec, Password


class InvalidStageException(MKGeneralException):
    pass


# TODO: This dataclass is already defined in
# cmk.gui.form_specs.vue.autogen_type_defs.vue_formspec_components
# but can't be imported here. Once we move this module, we can remove this
# and use the one from the other module.
@dataclass
class QuickSetupValidationError:
    message: str
    invalid_value: Any
    location: Sequence[str] = field(default_factory=list)


ValidationErrorMap = MutableMapping[FormSpecId, MutableSequence[QuickSetupValidationError]]


@dataclass
class StageOverview:
    title: str
    sub_title: str | None


@dataclass
class Errors:
    formspec_errors: ValidationErrorMap = field(default_factory=dict)
    stage_errors: GeneralStageErrors = field(default_factory=list)

    def exist(self) -> bool:
        return bool(self.formspec_errors or self.stage_errors)


@dataclass
class NextStageStructure:
    components: Sequence[dict]
    button_label: str | None


@dataclass
class Stage:
    next_stage_structure: NextStageStructure | None = None
    errors: Errors | None = None
    stage_recap: Sequence[Widget] = field(default_factory=list)


@dataclass
class QuickSetupOverview:
    quick_setup_id: QuickSetupId
    overviews: list[StageOverview]
    stage: Stage
    button_complete_label: str


def _get_stage_components_from_widget(widget: Widget) -> dict:
    if isinstance(widget, (ListOfWidgets, Collapsible)):
        widget_as_dict = asdict(widget)
        widget_as_dict["items"] = [_get_stage_components_from_widget(item) for item in widget.items]
        return widget_as_dict

    if isinstance(widget, FormSpecWrapper):
        form_spec = cast(FormSpec, widget.form_spec)
        return {
            "widget_type": widget.widget_type,
            "form_spec": asdict(
                serialize_data_for_frontend(
                    form_spec=form_spec,
                    field_id=str(widget.id),
                    origin=DataOrigin.DISK,
                    do_validate=False,
                ),
            ),
        }

    return asdict(widget)


def _stage_validate_all_form_spec_keys_existing(
    current_stage_form_data: RawFormData,
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> GeneralStageErrors:
    return [
        f"Formspec id '{form_spec_id}' not found"
        for form_spec_id in current_stage_form_data.keys()
        if form_spec_id not in expected_formspecs_map
    ]


def _form_spec_validate(
    all_stages_form_data: Sequence[RawFormData],
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> ValidationErrorMap:
    return {
        form_spec_id: [QuickSetupValidationError(**asdict(error)) for error in errors]
        for current_stage_form_data in all_stages_form_data
        for form_spec_id, form_data in current_stage_form_data.items()
        if (errors := validate_value_from_frontend(expected_formspecs_map[form_spec_id], form_data))
    }


def _form_spec_parse(
    all_stages_form_data: Sequence[RawFormData],
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> ParsedFormData:
    return {
        form_spec_id: parse_value_from_frontend(expected_formspecs_map[form_spec_id], form_data)
        for current_stage_form_data in all_stages_form_data
        for form_spec_id, form_data in current_stage_form_data.items()
    }


def _collect_params_with_defaults_from_form_data(
    all_stages_form_data: ParsedFormData, rulespec_name: str
) -> Mapping[str, object]:
    return _add_defaults_to_form_data(
        _get_rule_defaults(rulespec_name),
        collect_params_from_form_data(all_stages_form_data, rulespec_name),
    )


def _get_parameter_form_from_rulespec_name(rulespec_name: str) -> Dictionary | None:
    _parameter_form = form_spec_registry[rulespec_name.split(":")[1]].rule_spec.parameter_form
    return _parameter_form() if callable(_parameter_form) else _parameter_form


def collect_params_from_form_data(
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


def _check_preview_entry_by_service_interest(
    services_of_interest: Sequence[ServiceInterest],
    service_discovery_result: SpecialAgentDiscoveryPreviewResult,
) -> tuple[Mapping[ServiceInterest, list[CheckPreviewEntry]], list[CheckPreviewEntry]]:
    check_preview_entry_by_service_interest: Mapping[ServiceInterest, list[CheckPreviewEntry]] = {
        si: [] for si in services_of_interest
    }
    others: list[CheckPreviewEntry] = []
    for check_preview_entry in service_discovery_result.check_table:
        if matching_services_interests := _match_service_interest(
            check_preview_entry, services_of_interest
        ):
            check_preview_entry_by_service_interest[matching_services_interests].append(
                check_preview_entry
            )
        else:
            others.append(check_preview_entry)
    return check_preview_entry_by_service_interest, others


def _get_rule_defaults(rulespec_name: str) -> dict[str, object]:
    if (parameter_form := _get_parameter_form_from_rulespec_name(rulespec_name)) is None:
        return {}

    return serialize_data_for_frontend(
        form_spec=parameter_form,
        field_id="rule_id",
        origin=DataOrigin.DISK,
        do_validate=False,
    ).data


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


def _flatten_formspec_wrappers(components: Sequence[Widget]) -> Iterator[FormSpecWrapper]:
    for component in components:
        if isinstance(component, (ListOfWidgets, Collapsible)):
            yield from iter(_flatten_formspec_wrappers(component.items))

        if isinstance(component, FormSpecWrapper):
            yield component


def build_quick_setup_formspec_map(
    stages: Sequence[QuickSetupStage],
) -> Mapping[FormSpecId, FormSpec]:
    return {
        widget.id: cast(FormSpec, widget.form_spec)
        for stage in stages
        for widget in _flatten_formspec_wrappers(stage_components(stage))
    }


def stage_components(stage: QuickSetupStage) -> Sequence[Widget]:
    return (
        stage.configure_components()
        if callable(stage.configure_components)
        else stage.configure_components
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


def quick_setup_overview(quick_setup: QuickSetup) -> QuickSetupOverview:
    return QuickSetupOverview(
        quick_setup_id=quick_setup.id,
        overviews=[
            StageOverview(
                title=stage.title,
                sub_title=stage.sub_title,
            )
            for stage in quick_setup.stages
        ],
        stage=Stage(
            next_stage_structure=NextStageStructure(
                components=[
                    _get_stage_components_from_widget(widget)
                    for widget in stage_components(quick_setup.stages[0])
                ],
                button_label=quick_setup.stages[0].button_label,
            ),
        ),
        button_complete_label=quick_setup.button_complete_label,
    )


def validate_stage(
    stage: QuickSetupStage,
    formspec_lookup: Mapping[FormSpecId, FormSpec],
    stages_raw_formspecs: Sequence[RawFormData],
) -> Errors | None:
    errors = Errors()

    errors.stage_errors.extend(
        _stage_validate_all_form_spec_keys_existing(stages_raw_formspecs[-1], formspec_lookup)
    )
    errors.formspec_errors = _form_spec_validate(stages_raw_formspecs, formspec_lookup)
    if errors.exist():
        return errors

    parsed_formspecs_data = _form_spec_parse(stages_raw_formspecs, formspec_lookup)

    for custom_validator in stage.custom_validators:
        errors.stage_errors.extend(
            custom_validator(
                parsed_formspecs_data,
                formspec_lookup,
            )
        )

    return errors if errors.exist() else None


def retrieve_next_stage(
    quick_setup: QuickSetup,
    incoming_stages: Sequence[IncomingStage],
) -> Stage:
    current_stage_index = len(incoming_stages) - 1
    current_stage = quick_setup.stages[current_stage_index]

    quick_setup_formspec_map = build_quick_setup_formspec_map(quick_setup.stages)
    combined_parsed_form_data_by_stage = [
        _form_spec_parse([stage.form_data], quick_setup_formspec_map) for stage in incoming_stages
    ]

    current_stage_recap = [
        r
        for recap_callable in current_stage.recap
        for r in recap_callable(
            combined_parsed_form_data_by_stage,
            quick_setup_formspec_map,
        )
    ]

    if current_stage_index == len(quick_setup.stages) - 1:
        return Stage(next_stage_structure=None, stage_recap=current_stage_recap)

    next_stage = quick_setup.stages[current_stage_index + 1]

    return Stage(
        next_stage_structure=NextStageStructure(
            components=[
                _get_stage_components_from_widget(widget) for widget in stage_components(next_stage)
            ],
            button_label=next_stage.button_label,
        ),
        stage_recap=current_stage_recap,
    )


def complete_quick_setup(
    quick_setup: QuickSetup,
    incoming_stages: Sequence[IncomingStage],
) -> QuickSetupSaveRedirect:
    if quick_setup.save_action is None:
        return QuickSetupSaveRedirect(redirect_url=None)

    return QuickSetupSaveRedirect(
        redirect_url=quick_setup.save_action(
            _form_spec_parse(
                [stage.form_data for stage in incoming_stages],
                build_quick_setup_formspec_map(quick_setup.stages),
            )
        )
    )
