#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence

from livestatus import SiteConfiguration

from cmk.ccc.site import SiteId
from cmk.gui.form_specs.unstable.two_column_dictionary import TwoColumnDictionary
from cmk.gui.i18n import _
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
    ProgressLogger,
    QuickSetup,
    QuickSetupActionButtonIcon,
    QuickSetupActionMode,
    QuickSetupBackgroundAction,
    QuickSetupBackgroundStageAction,
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
from cmk.plugins.azure_v2.rulesets import (  # astrein: disable=cmk-module-layer-violation  # TODO: acceptable?
    azure,
)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary
from cmk.utils.rulesets.definition import RuleGroup

NEXT_BUTTON_ARIA_LABEL = _("Go to the next stage")
PREV_BUTTON_ARIA_LABEL = _("Go to the previous stage")
PREV_BUTTON_LABEL = _("Back")


FIRST_LEVEL_DICT_TITLES: dict[str, Title] = {
    "proxy": Title("HTTP proxy"),
    "filter_tags": Title("Filter tags"),
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
                            "Register an app in Entra ID. Note down the Directory (tenant) ID and Application (client) ID. Additionally, note down one or more Subscription IDs if you plan to monitor Azure Resource Manager (ARM) resources."
                        )
                    ),
                    Text(
                        text=_(
                            'If you plan to monitor Azure resources via Azure Resource Manager, assign the built-in Reader role to the app at the subscription (or appropriate resource group) level in Access control (IAM). Additionally, if resources available through the Graph API will be monitored, add the Microsoft Graph application permissions "Directory.Read.All" and "User.Read.All" and grant admin consent. These resources include "Users in Entra ID", "Entra Connect Sync", and "App Registrations".'
                        ),
                    ),
                    Text(text=_("Create a client secret for the app and note it down.")),
                    Text(
                        text=_(
                            "Return to Checkmk, define a unique configuration name, and enter the tenant ID, client ID, client secret, and subscription ID(s) (if applicable) below."
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
                form_spec=TwoColumnDictionary(
                    elements=_add_first_level_keys_to_config_dict(
                        azure.configuration_authentication()
                    ),
                ),
            ),
        ],
        actions=[
            QuickSetupBackgroundStageAction(
                id=ActionId("action"),
                custom_validators=[
                    qs_validators.validate_unique_id,
                    qs_validators.validate_non_quick_setup_password(
                        parameter_form=azure.formspec()
                    ),
                    qs_validators.validate_test_connection_custom_collect_params(
                        rulespec_name=RuleGroup.SpecialAgents("azure_v2"),
                        parameter_form=azure.formspec(),
                        custom_collect_params=_collect_params_for_connection_test,
                        error_message=_(
                            "Could not access your Azure account. Please check your credentials "
                            "and/or HTTP proxy setting."
                        ),
                    ),
                ],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Configure host and authority"),
                permissions=["wato.passwords"],
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
            widgets.host_name_and_host_path_formspec_wrapper(host_prefill_template="azure_v2"),
            widgets.site_formspec_wrapper(),
        ],
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[
                    qs_validators.validate_host_name_doesnt_exists,
                    qs_validators.validate_host_path_permissions,
                ],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Configure services to monitor"),
                permissions=["wato.hosts"],
            ),
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def _configure() -> Sequence[Widget]:
    return [
        FormSpecWrapper(
            id=FormSpecId("configure_services_to_monitor"),
            form_spec=TwoColumnDictionary(
                elements=azure.configuration_services(),
            ),
        ),
        Collapsible(
            title="Other options",
            items=[
                FormSpecWrapper(
                    id=FormSpecId("configure_advanced"),
                    form_spec=TwoColumnDictionary(
                        elements=_add_first_level_keys_to_config_dict(
                            azure.configuration_advanced()
                        ),
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
    progress_logger: ProgressLogger,
    site_configs: Mapping[SiteId, SiteConfiguration],
    debug: bool,
) -> Sequence[Widget]:
    service_discovery_result = utils.get_service_discovery_preview(
        rulespec_name=RuleGroup.SpecialAgents("azure_v2"),
        all_stages_form_data=parsed_data,
        parameter_form=azure.formspec(),
        collect_params=azure_collect_params,
        progress_logger=progress_logger,
        site_configs=site_configs,
        debug=debug,
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
            QuickSetupBackgroundStageAction(
                id=ActionId("action"),
                custom_validators=[],
                recap=[
                    recap_found_services,
                ],
                next_button_label=_("Test configuration"),
                load_wait_label=_("This process may take several minutes, please wait..."),
            ),
            QuickSetupStageAction(
                id=ActionId("skip_configuration_test"),
                custom_validators=[],
                recap=[
                    lambda *args, **kwargs: [
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
    progress_logger: ProgressLogger,
    _object_id: str | None,
    use_git: bool,
    pprint_value: bool,
) -> str:
    match mode:
        case QuickSetupActionMode.SAVE:
            return complete.create_and_save_special_agent_bundle_custom_collect_params(
                special_agent_name="azure_v2",
                parameter_form=azure.formspec(),
                all_stages_form_data=all_stages_form_data,
                custom_collect_params=azure_collect_params,
                progress_logger=progress_logger,
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
    title=_("Azure"),
    id=QuickSetupId(RuleGroup.SpecialAgents("azure_v2")),
    stages=[
        configure_authentication,
        configure_host_and_authority,
        configure_services_to_monitor,
        review_and_run_preview_service_discovery,
    ],
    actions=[
        QuickSetupBackgroundAction(
            id=ActionId("activate_changes"),
            label=_("Save & go to Activate changes"),
            icon=QuickSetupActionButtonIcon(name="save-to-services"),
            action=action,
            permissions=["wato.passwords", "wato.rulesets", "wato.hosts"],
        ),
    ],
)
