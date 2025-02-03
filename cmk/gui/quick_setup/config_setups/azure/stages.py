#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.ccc.i18n import _

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.form_specs.private.dictionary_extended import DictionaryExtended
from cmk.gui.quick_setup.v0_unstable.predefined import (
    collect_params_from_form_data,
    collect_params_with_defaults_from_form_data,
    complete,
    recaps,
    utils,
    widgets,
)
from cmk.gui.quick_setup.v0_unstable.predefined import validators as qs_validators
from cmk.gui.quick_setup.v0_unstable.setups import (
    QuickSetup,
    QuickSetupAction,
    QuickSetupActionMode,
    QuickSetupStage,
    QuickSetupStageAction,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ActionId,
    ParsedFormData,
    QuickSetupId,
    ServiceInterest,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import (
    Collapsible,
    FormSpecId,
    FormSpecWrapper,
    ListOfWidgets,
    Text,
    Widget,
)

from cmk.plugins.azure.rulesets import azure  # pylint: disable=cmk-module-layer-violation
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary
from cmk.shared_typing.vue_formspec_components import DictionaryLayout

NEXT_BUTTON_ARIA_LABEL = _("Go to the next stage")
PREV_BUTTON_ARIA_LABEL = _("Go to the previous stage")
PREV_BUTTON_LABEL = _("Back")


FIRST_LEVEL_DICT_TITLES: dict[str, Title] = {
    "proxy": Title("HTTP proxy"),
    "piggyback_vms": Title("Map data"),
    "import_tags": Title("Tags"),
}


def _add_first_level_keys_to_config_dict(
    config_dict: Mapping[str, DictElement],
) -> Mapping[str, DictElement]:
    """This ensures we have required first level keys, i.e. keys without a leading checkbox.
    The duplicate keys are later removed in azure_transform_to_disk()."""
    return {
        **config_dict,
        **{
            key: DictElement(
                parameter_form=Dictionary(
                    title=title,
                    elements={key: config_dict[key]},
                ),
                required=True,
            )
            for key, title in FIRST_LEVEL_DICT_TITLES.items()
            if key in config_dict
        },
    }


def _collect_params_for_connection_test(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    """For the quick setup validation of the Azure authentication we run a connection test only.
    The agent option "--connection-test" is added, running only a connection via the Management API
    client (none via the Graph API client)."""
    return {
        **azure_transform_to_disk(
            collect_params_with_defaults_from_form_data(all_stages_form_data, parameter_form)
        ),
        "connection_test": True,
    }


def configure_authentication() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Prepare Azure for Checkmk"),
        configure_components=[
            ListOfWidgets(
                items=[
                    Text(
                        text=_(
                            "Register an app in Entra ID. Note down the Directory (tenant) ID, Application (client) ID as well as the used Subscription ID."
                        )
                    ),
                    Text(
                        text=_(
                            'Assign the built-in role "Reader" to the app in the Access control (IAM). Additionally add the application permissions "Directory.Read.All" and "User.Read.All" to the app if resources available through the Graph API will be monitored. These resources include "Users in Entra ID", "Entra Connect Sync", "App Registrations".'
                        ),
                    ),
                    Text(text=_("Create a client secret for the app and note it down.")),
                    Text(
                        text=_(
                            "Return to Checkmk, define a unique configuration name, and use the Subscription ID, Tenant ID, Client ID, and the Client secret below. Please note that the Subscription ID is not needed if only monitoring resources through the Graph API."
                        )
                    ),
                ],
                list_type="ordered",
            ),
            widgets.unique_id_formspec_wrapper(
                title=Title("Configuration name"), prefill_template="azure_config"
            ),
            FormSpecWrapper(
                id=FormSpecId("credentials"),
                form_spec=DictionaryExtended(
                    elements=_add_first_level_keys_to_config_dict(
                        azure.configuration_authentication()
                    ),
                    layout=DictionaryLayout.two_columns,
                    prefill=DefaultValue({"subscription": ""}),
                ),
            ),
        ],
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[
                    qs_validators.validate_unique_id,
                    qs_validators.validate_test_connection_custom_collect_params(
                        rulespec_name=RuleGroup.SpecialAgents("azure"),
                        parameter_form=azure.formspec(),
                        custom_collect_params=_collect_params_for_connection_test,
                        error_message=_(
                            "Could not access your Azure account. Please check your credentials."
                        ),
                    ),
                ],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Configure host and authority"),
                run_in_background=True,
            ),
        ],
    )


def configure_host_and_authority() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure host"),
        sub_title=_(
            "Name your host and define the folder",
        ),
        configure_components=[
            widgets.host_name_and_host_path_formspec_wrapper(host_prefill_template="azure"),
            widgets.site_formspec_wrapper(),
        ],
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[qs_validators.validate_host_name_doesnt_exists],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Configure services to monitor"),
            ),
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def _configure() -> Sequence[Widget]:
    return [
        FormSpecWrapper(
            id=FormSpecId("configure_services_to_monitor"),
            form_spec=DictionaryExtended(
                elements=azure.configuration_services(),
                layout=DictionaryLayout.two_columns,
            ),
        ),
        Collapsible(
            title="Other options",
            items=[
                FormSpecWrapper(
                    id=FormSpecId("configure_advanced"),
                    form_spec=DictionaryExtended(
                        elements=_add_first_level_keys_to_config_dict(
                            azure.configuration_advanced()
                        ),
                        layout=DictionaryLayout.two_columns,
                    ),
                ),
            ],
        ),
    ]


def configure_services_to_monitor() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure services to monitor"),
        sub_title=_("Select and configure the Microsoft Azure services you would like to monitor"),
        configure_components=_configure,
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[],
                recap=[
                    recaps.recaps_form_spec,
                ],
                next_button_label=_("Review and test configuration"),
            )
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def recap_found_services(
    _quick_setup_id: QuickSetupId,
    _stage_index: StageIndex,
    parsed_data: ParsedFormData,
) -> Sequence[Widget]:
    service_discovery_result = utils.get_service_discovery_preview(
        rulespec_name=RuleGroup.SpecialAgents("azure"),
        all_stages_form_data=parsed_data,
        parameter_form=azure.formspec(),
        collect_params=azure_collect_params,
    )
    azure_service_interest = ServiceInterest(r"(?i).*azure.*", "services")
    filtered_groups_of_services, _other_services = utils.group_services_by_interest(
        services_of_interest=[azure_service_interest],
        service_discovery_result=service_discovery_result,
    )
    if len(filtered_groups_of_services[azure_service_interest]):
        return [
            Text(text=_("Azure services found!")),
            Text(text=_("Save your progress and go to the Activate Changes page to enable it.")),
        ]
    return [
        Text(text=_("No Azure services found.")),
        Text(
            text=_(
                "The connection to Azure was successful, but no services were found. If this is unintentional, please verify your configuration."
            )
        ),
    ]


def review_and_run_preview_service_discovery() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Review and run preview service discovery"),
        sub_title=_("Review your configuration and run preview service discovery"),
        configure_components=[],
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[],
                recap=[
                    recap_found_services,
                ],
                next_button_label=_("Test configuration"),
                load_wait_label=_("This process may take several minutes, please wait..."),
                run_in_background=True,
            ),
            QuickSetupStageAction(
                id=ActionId("skip_configuration_test"),
                custom_validators=[],
                recap=[
                    lambda __, ___, ____: [
                        Text(text=_("Skipped the configuration test.")),
                        Text(
                            text=_(
                                "Save your progress and go to the Activate Changes page to enable it."
                            )
                        ),
                    ]
                ],
                next_button_label=_("Skip test"),
            ),
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def action(
    all_stages_form_data: ParsedFormData,
    mode: QuickSetupActionMode,
    object_id: str | None,
) -> str:
    match mode:
        case QuickSetupActionMode.SAVE:
            return complete.create_and_save_special_agent_bundle_custom_collect_params(
                special_agent_name="azure",
                parameter_form=azure.formspec(),
                all_stages_form_data=all_stages_form_data,
                custom_collect_params=azure_collect_params,
            )
        case QuickSetupActionMode.EDIT:
            raise ValueError("Edit mode not supported")
        case _:
            raise ValueError(f"Unknown mode {mode}")


def azure_transform_to_disk(params: Mapping[str, object]) -> Mapping[str, object]:
    # "Unwrap" config dicts where we introduced duplicate first level keys before
    transformed = dict(params)
    for key in FIRST_LEVEL_DICT_TITLES:
        if key in transformed:
            tmp_dict = transformed[key]
            assert isinstance(tmp_dict, dict)
            if key in tmp_dict:
                transformed[key] = tmp_dict[key]
            else:
                del transformed[key]
    return transformed


def azure_collect_params(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    return azure_transform_to_disk(
        collect_params_from_form_data(all_stages_form_data, parameter_form)
    )


quick_setup_azure = QuickSetup(
    title=_("Microsoft Azure"),
    id=QuickSetupId(RuleGroup.SpecialAgents("azure")),
    stages=[
        configure_authentication,
        configure_host_and_authority,
        configure_services_to_monitor,
        review_and_run_preview_service_discovery,
    ],
    actions=[
        QuickSetupAction(
            id=ActionId("activate_changes"),
            label=_("Save & go to Activate changes"),
            action=action,
            run_in_background=True,
        ),
    ],
)
