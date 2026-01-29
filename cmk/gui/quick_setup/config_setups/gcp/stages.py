#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence

from livestatus import SiteConfiguration

from cmk.ccc.site import SiteId
from cmk.gui.form_specs.unstable.two_column_dictionary import TwoColumnDictionary
from cmk.gui.htmllib.generator import HTMLWriter
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
from cmk.gui.utils.urls import doc_reference_url, DocReference
from cmk.plugins.gcp.rulesets import gcp  # astrein: disable=cmk-module-layer-violation
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.utils.rulesets.definition import RuleGroup

NEXT_BUTTON_ARIA_LABEL = _("Go to the next stage")
PREV_BUTTON_ARIA_LABEL = _("Go to the previous stage")
PREV_BUTTON_LABEL = _("Back")


def _collect_params_for_connection_test(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    """For the quick setup validation of the AWS authentication we run a connection test only using
    the agent option "--connection-test"."""
    return {
        **collect_params_with_defaults_from_form_data(all_stages_form_data, parameter_form),
        "connection_test": True,
    }


def configure_authentication() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Prepare GCP for Checkmk"),
        configure_components=[
            ListOfWidgets(
                items=[
                    Text(
                        text=_(
                            "Log in to the Google Cloud Console, select the project to monitor and note down the Project ID either from the dashboard or project settings."
                        )
                    ),
                    Text(
                        text=_(
                            'Create a Service Account in "IAM & Admin" and assign the roles "Monitoring Viewer" and "Cloud Asset Viewer" to this account.'
                        ),
                    ),
                    Text(
                        text=_(
                            "Create a new key in JSON format for the service account and download the created file."
                        )
                    ),
                    Text(
                        text=_(
                            'Verify that the "Cloud Asset API" on "APIs & Serivces" is activated. It may take some minutes until the API is accessible.'
                        )
                    ),
                    Text(
                        text=_(
                            "Return to Checkmk, define a unique configuration name, and use the project ID as well as the raw output of the JSON file for the key below."
                        )
                    ),
                ],
                list_type="ordered",
            ),
            widgets.unique_id_formspec_wrapper(
                title=Title("Configuration name"), prefill_template="gcp_config"
            ),
            FormSpecWrapper(
                id=FormSpecId("credentials"),
                form_spec=TwoColumnDictionary(
                    elements=gcp.configuration_authentication(),
                ),
            ),
        ],
        actions=[
            QuickSetupBackgroundStageAction(
                id=ActionId("action"),
                custom_validators=[
                    qs_validators.validate_unique_id,
                    qs_validators.validate_non_quick_setup_password(parameter_form=gcp.form_spec()),
                    qs_validators.validate_test_connection_custom_collect_params(
                        rulespec_name=RuleGroup.SpecialAgents("gcp"),
                        parameter_form=gcp.form_spec(),
                        custom_collect_params=_collect_params_for_connection_test,
                        error_message=_(
                            "Could not access your GCP account. Please check your credentials."
                        ),
                    ),
                ],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Configure host"),
                permissions=["wato.passwords"],
            )
        ],
    )


def configure_host() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure host"),
        sub_title=_("Name your host and define the folder path"),
        configure_components=[
            widgets.host_name_and_host_path_formspec_wrapper(host_prefill_template="gcp"),
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
            )
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def _configure() -> Sequence[Widget]:
    return [
        FormSpecWrapper(
            id=FormSpecId("configure_services_to_monitor"),
            form_spec=TwoColumnDictionary(
                elements=gcp.configuration_services(),
            ),
        ),
        Collapsible(
            title="Other options",
            items=[
                FormSpecWrapper(
                    id=FormSpecId("configure_advanced"),
                    form_spec=TwoColumnDictionary(
                        elements=gcp.configuration_services_advanced(),
                    ),
                ),
            ],
        ),
    ]


def configure_services_to_monitor() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure services to monitor"),
        sub_title=_(
            "Select and configure the Google Cloud Platform services you would like to monitor"
        ),
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


class _GCERecapMessage:
    @staticmethod
    def _cre_message() -> str:
        return _(
            "Hosts for virtual machines need to be created manually, please check the %s."
        ) % HTMLWriter.render_a(
            _("documentation"),
            href=doc_reference_url(DocReference.GCP_MANUAL_VM),
        )

    message: Callable[[], str] = _cre_message


gce_recap_message = _GCERecapMessage()


def _save_and_activate_recap(title: str, parsed_data: ParsedFormData) -> Sequence[Widget]:
    message = _("Save your progress and go to the Activate Changes page to enable it.")
    if "gce" in parsed_data.get(FormSpecId("configure_advanced"), {}).get("piggyback", {}).get(
        "piggyback_services", []
    ):
        message += " " + gce_recap_message.message()
    return [
        Text(text=title),
        Text(text=message),
    ]


def recap_found_services(
    _quick_setup_id: QuickSetupId,
    _stage_index: StageIndex,
    parsed_data: ParsedFormData,
    progress_logger: ProgressLogger,
    site_configs: Mapping[SiteId, SiteConfiguration],
    debug: bool,
) -> Sequence[Widget]:
    service_discovery_result = utils.get_service_discovery_preview(
        rulespec_name=RuleGroup.SpecialAgents("gcp"),
        all_stages_form_data=parsed_data,
        parameter_form=gcp.form_spec(),
        collect_params=gcp_collect_params,
        progress_logger=progress_logger,
        site_configs=site_configs,
        debug=debug,
    )
    gcp_service_interest = ServiceInterest("gcp_.*", "services")
    filtered_groups_of_services, _other_services = utils.group_services_by_interest(
        services_of_interest=[gcp_service_interest],
        service_discovery_result=service_discovery_result,
    )
    if len(filtered_groups_of_services[gcp_service_interest]):
        return _save_and_activate_recap(_("GCP services found!"), parsed_data)
    return [
        Text(text=_("No GCP services found.")),
        Text(
            text=_(
                "The connection to GCP was successful, but no services were found. If this is unintentional, please verify your configuration."
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
                recap=[recap_found_services],
                next_button_label=_("Test configuration"),
                load_wait_label=_("This process may take several minutes, please wait..."),
            ),
            QuickSetupStageAction(
                id=ActionId("skip_configuration_test"),
                custom_validators=[],
                recap=[
                    lambda _a, _b, parsed_data, *args, **kargs: _save_and_activate_recap(
                        _("Skipped the configuration test."), parsed_data
                    )
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
                special_agent_name="gcp",
                parameter_form=gcp.form_spec(),
                all_stages_form_data=all_stages_form_data,
                custom_collect_params=gcp_collect_params,
                progress_logger=progress_logger,
            )
        case QuickSetupActionMode.EDIT:
            raise ValueError("Edit mode not supported")
        case _:
            raise ValueError(f"Unknown mode {mode}")


def gcp_collect_params(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    return collect_params_from_form_data(all_stages_form_data, parameter_form)


quick_setup_gcp = QuickSetup(
    title=_("Google Cloud Platform (GCP)"),
    id=QuickSetupId(RuleGroup.SpecialAgents("gcp")),
    stages=[
        configure_authentication,
        configure_host,
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
