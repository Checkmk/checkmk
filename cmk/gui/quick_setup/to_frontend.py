#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator, Mapping, MutableMapping, MutableSequence, Sequence
from dataclasses import asdict, dataclass, field
from functools import partial
from typing import Any, cast
from uuid import uuid4

from livestatus import SiteId

from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_QUICK_SETUP
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.password_store import Password as StorePassword
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RuleConditionsSpec, RuleSpec

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
from cmk.gui.form_specs.vue.registries import form_spec_registry
from cmk.gui.form_specs.vue.visitors._type_defs import DataOrigin
from cmk.gui.http import request
from cmk.gui.i18n import ungettext
from cmk.gui.quick_setup.v0_unstable.definitions import (
    IncomingStage,
    QuickSetupSaveRedirect,
    UniqueBundleIDStr,
)
from cmk.gui.quick_setup.v0_unstable.setups import (
    CallableRecap,
    CallableValidator,
    QuickSetup,
    QuickSetupStage,
)
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
    FormSpecRecap,
    FormSpecWrapper,
    ListOfWidgets,
    Text,
    Widget,
)
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.wato.pages.activate_changes import ModeActivateChanges
from cmk.gui.watolib.check_mk_automations import diag_special_agent, special_agent_discovery_preview
from cmk.gui.watolib.configuration_bundles import (
    BundleId,
    ConfigBundle,
    ConfigBundleStore,
    create_config_bundle,
    CreateBundleEntities,
    CreateHost,
    CreatePassword,
    CreateRule,
)
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.passwords import load_passwords
from cmk.gui.watolib.services import get_check_table, perform_fix_all

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site
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
        _collect_params_from_form_data(all_stages_form_data, rulespec_name),
    )


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


def _form_data_to_diag_special_agent_input(
    rulespec_name: str,
    all_stages_form_data: ParsedFormData,
) -> DiagSpecialAgentInput:
    host_name = _find_unique_id(all_stages_form_data, "host_name")
    return DiagSpecialAgentInput(
        host_config=DiagSpecialAgentHostConfig(
            host_name=HostName(host_name or ""), host_alias=host_name or ""
        ),
        agent_name=rulespec_name.split(":")[1],
        params=_collect_params_with_defaults_from_form_data(all_stages_form_data, rulespec_name),
        passwords=_collect_passwords_from_form_data(all_stages_form_data, rulespec_name),
    )


def validate_test_connection(rulespec_name: str) -> CallableValidator:
    return partial(_validate_test_connection, rulespec_name)


def _validate_test_connection(
    rulespec_name: str,
    all_stages_form_data: ParsedFormData,
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> GeneralStageErrors:
    general_errors: GeneralStageErrors = []
    site_id = _find_unique_id(all_stages_form_data, "site_selection")
    output = diag_special_agent(
        SiteId(site_id) if site_id else omd_site(),
        _form_data_to_diag_special_agent_input(rulespec_name, all_stages_form_data),
    )
    for result in output.results:
        if result.return_code != 0:
            general_errors.append(result.response)
    return general_errors


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


def recap_service_discovery(
    rulespec_name: str,
    services_of_interest: Sequence[ServiceInterest],
) -> CallableRecap:
    return partial(_recap_service_discovery, rulespec_name, services_of_interest)


def _recap_service_discovery(
    rulespec_name: str,
    services_of_interest: Sequence[ServiceInterest],
    all_stages_form_data: Sequence[ParsedFormData],
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> Sequence[Widget]:
    combined_parsed_form_data = {
        k: v for form_data in all_stages_form_data for k, v in form_data.items()
    }
    site_id = _find_unique_id(all_stages_form_data, "site_selection")

    service_discovery_result = special_agent_discovery_preview(
        SiteId(site_id) if site_id else omd_site(),
        _form_data_to_diag_special_agent_input(rulespec_name, combined_parsed_form_data),
    )
    check_preview_entry_by_service_interest, others = _check_preview_entry_by_service_interest(
        services_of_interest, service_discovery_result
    )
    items: list[Widget] = [
        Text(
            text=f"{len(check_preview_entries)} {service_interest.label}",
        )
        for service_interest, check_preview_entries in check_preview_entry_by_service_interest.items()
    ]
    if len(others) >= 1:
        items.append(Text(text=ungettext("%s other service", "%s other services", len(others))))

    return [ListOfWidgets(items=items, list_type="check")]


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
        for widget in _flatten_formspec_wrappers(stage.configure_components)
    }


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


def validate_unique_id(
    stages_form_data: ParsedFormData,
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> GeneralStageErrors:
    bundle_id = _find_unique_id(stages_form_data, UniqueBundleIDStr)
    if bundle_id is None:
        return [f"Expected the key '{UniqueBundleIDStr}' in the form data"]

    if bundle_id in ConfigBundleStore().load_for_reading():
        return [f'Configuration bundle "{bundle_id}" already exists.']

    return []


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
                    for widget in quick_setup.stages[0].configure_components
                ],
                button_label=quick_setup.stages[0].button_label,
            ),
        ),
        button_complete_label=quick_setup.button_complete_label,
    )


def recaps_form_spec(
    stages_form_data: Sequence[ParsedFormData],
    expected_formspecs_map: Mapping[FormSpecId, FormSpec],
) -> Sequence[Widget]:
    return [
        FormSpecRecap(
            id=form_spec_id,
            form_spec=serialize_data_for_frontend(
                form_spec=expected_formspecs_map[form_spec_id],
                field_id=form_spec_id,
                origin=DataOrigin.DISK,
                do_validate=False,
                value=form_data,
            ),
        )
        for form_spec_id, form_data in stages_form_data[-1].items()
        if form_spec_id in expected_formspecs_map
    ]


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
                _get_stage_components_from_widget(widget)
                for widget in next_stage.configure_components
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


def create_host_from_form_data(
    host_name: HostName,
    host_path: str,
) -> CreateHost:
    return CreateHost(
        name=host_name,
        folder=host_path,
        attributes=HostAttributes(
            ipaddress=HostAddress("127.0.0.1")  # TODO: CMK-18691 IP address should not be required
        ),
    )


def create_password_from_form_data(
    all_stages_form_data: ParsedFormData,
    rulespec_name: str,
    bundle_id: BundleId,
) -> Sequence[CreatePassword]:
    return [
        CreatePassword(
            id=pw_id,
            spec=StorePassword(
                title=f"{bundle_id}_password",
                comment="",
                docu_url="",
                password=password,
                owned_by=None,
                shared_with=[],
            ),
        )
        for pw_id, password in _collect_passwords_from_form_data(
            all_stages_form_data=all_stages_form_data,
            rulespec_name=rulespec_name,
        ).items()
    ]


def create_rule_from_form_data(
    all_stages_form_data: ParsedFormData,
    host_name: str,
    host_path: str,
    rulespec_name: str,
    bundle_id: BundleId,
    site_id: str,
) -> CreateRule:
    return CreateRule(
        folder=host_path,
        ruleset=rulespec_name,
        spec=RuleSpec(
            value=_collect_params_with_defaults_from_form_data(
                all_stages_form_data=all_stages_form_data,
                rulespec_name=rulespec_name,
            ),
            id=str(uuid4()),
            locked_by=GlobalIdent(
                site_id=site_id,
                program_id=PROGRAM_ID_QUICK_SETUP,
                instance_id=bundle_id,
            ),
            condition=RuleConditionsSpec(
                host_tags={},
                host_label_groups=[],
                host_name=[host_name],
                host_folder=host_path,
            ),
        ),
    )


def create_and_save_special_agent_bundle(
    special_agent_name: str,
    all_stages_form_data: ParsedFormData,
) -> str:
    rulespec_name = RuleGroup.SpecialAgents(special_agent_name)
    bundle_id = _find_unique_id(form_data=all_stages_form_data, target_key=UniqueBundleIDStr)
    if bundle_id is None:
        raise ValueError("No bundle id found")

    host_name = all_stages_form_data[FormSpecId("host_data")]["host_name"]
    host_path = all_stages_form_data[FormSpecId("host_data")]["host_path"]

    site_selection = _find_unique_id(all_stages_form_data, "site_selection")

    # TODO: DCD still to be implemented cmk-18341
    create_config_bundle(
        bundle_id=BundleId(bundle_id),
        bundle=ConfigBundle(
            title=f"{bundle_id}_config",
            comment="",
            group=rulespec_name,
            program_id=PROGRAM_ID_QUICK_SETUP,
        ),
        entities=CreateBundleEntities(
            hosts=[create_host_from_form_data(host_name=HostName(host_name), host_path=host_path)],
            passwords=create_password_from_form_data(
                all_stages_form_data=all_stages_form_data,
                rulespec_name=rulespec_name,
                bundle_id=BundleId(bundle_id),
            ),
            rules=[
                create_rule_from_form_data(
                    all_stages_form_data=all_stages_form_data,
                    host_name=host_name,
                    host_path=host_path,
                    rulespec_name=rulespec_name,
                    bundle_id=BundleId(bundle_id),
                    site_id=SiteId(site_selection) if site_selection else omd_site(),
                )
            ],
        ),
    )

    # TODO: config sync

    host: Host = Host.load_host(host_name)
    perform_fix_all(
        discovery_result=get_check_table(host=host, action=host_name, raise_errors=False),
        host=host,
        raise_errors=False,
    )

    return makeuri_contextless(
        request,
        [("mode", ModeActivateChanges.name())],
        filename="wato.py",
    )
