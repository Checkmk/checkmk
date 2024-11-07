#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.ccc.i18n import _

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.form_specs.private.dictionary_extended import DictionaryExtended
from cmk.gui.form_specs.vue.shared_type_defs import DictionaryLayout
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
)
from cmk.gui.quick_setup.v0_unstable.type_defs import (
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

from cmk.plugins.azure.rulesets import (  # pylint: disable=cmk-module-layer-violation
    azure,
)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, Dictionary

NEXT_BUTTON_ARIA_LABEL = _("Go to the next stage")
PREV_BUTTON_ARIA_LABEL = _("Go to the previous stage")
PREV_BUTTON_LABEL = _("Back")


def _collect_params_for_connection_test(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    """For the quick setup validation of the Azure authentication we run a connection test only.
    The agent option "--connection-test" is added, running only a connection via the Management API
    client (none via the Graph API client)."""
    return {
        **collect_params_with_defaults_from_form_data(all_stages_form_data, parameter_form),
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
                            "Create an Azure app for Checkmk: Register the app in Azure Active Directory and note down the Application ID."
                        )
                    ),
                    Text(
                        text=_(
                            'Assign permissions to the app: Grant necessary access rights, assigning the "Reader" role.'
                        ),
                    ),
                    Text(
                        text=_(
                            "Generate a key for the app: Create a Secret key in the app settings and note it down."
                        )
                    ),
                    Text(
                        text=_(
                            "Retrieve required information: Gather Subscription ID, Tenant ID, Client ID, and the Client secret from Azure."
                        )
                    ),
                    Text(
                        text=_(
                            "Return to Checkmk: Define a unique Azure account name, and use the  Subscription ID, Tenant ID, Client ID, and the Client secret below."
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
                    elements=azure.configuration_authentication(),
                    layout=DictionaryLayout.two_columns,
                    prefill=DefaultValue({"subscription": ""}),
                ),
            ),
        ],
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
        custom_validators=[qs_validators.validate_host_name_doesnt_exists],
        recap=[recaps.recaps_form_spec],
        next_button_label=_("Configure services to monitor"),
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
                        elements=azure.configuration_advanced(),
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
        custom_validators=[],
        recap=[
            recaps.recaps_form_spec,
        ],
        next_button_label=_("Review and test configuration"),
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
        custom_validators=[],
        recap=[
            recap_found_services,
        ],
        next_button_label=_("Test configuration"),
        prev_button_label=PREV_BUTTON_LABEL,
        load_wait_label=_("This process may take several minutes, please wait..."),
    )


def action(
    all_stages_form_data: ParsedFormData, mode: QuickSetupActionMode, object_id: str | None
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


def azure_collect_params(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    return collect_params_from_form_data(all_stages_form_data, parameter_form)


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
            id="activate_changes",
            label=_("Save & go to Activate changes"),
            action=action,
        ),
    ],
)
