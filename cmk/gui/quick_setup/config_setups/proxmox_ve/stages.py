#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
    NoteText,
    Text,
    Widget,
)
from cmk.plugins.proxmox_ve.rulesets import (  # astrein: disable=cmk-module-layer-violation
    proxmox_ve,
)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.utils.rulesets.definition import RuleGroup

PREV_BUTTON_LABEL = _("Back")


def _collect_params_for_connection_test(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    """For the quick setup validation of the Proxmox VE authentication we run a connection test
    only, using the special agent option "--connection-test"."""
    return {
        **collect_params_with_defaults_from_form_data(all_stages_form_data, parameter_form),
        "connection_test": True,
    }


def configure_host() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure Proxmox VE host"),
        sub_title=_(
            "Enter a unique configuration ID, your Proxmox VE node's host name and define the "
            "folder path where nodes and VMs should be created"
        ),
        configure_components=[
            widgets.unique_id_formspec_wrapper(
                title=Title("Configuration name"), prefill_template="proxmox_ve_config"
            ),
            widgets.host_name_and_host_path_formspec_wrapper(host_prefill_template="proxmox_ve"),
            widgets.site_formspec_wrapper(),
        ],
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[
                    qs_validators.validate_unique_id,
                    qs_validators.validate_host_name_doesnt_exists,
                    qs_validators.validate_host_path_permissions,
                ],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Configure Proxmox VE authentication"),
                permissions=["wato.hosts"],
            )
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def configure_authentication() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure Proxmox VE authentication for Checkmk"),
        sub_title=_("Configure a Proxmox VE API user to fetch node and VM information"),
        configure_components=[
            ListOfWidgets(
                items=[
                    Text(
                        text=_(
                            "Create a user in the 'Proxmox VE authentication server' realm in "
                            "Proxmox, which you use exclusively for monitoring with Checkmk"
                        )
                    ),
                    Text(
                        text=_(
                            'Grant the user the permissions "Role: PVEAuditor" and "Path: /" '
                            "(via User permissions or Group permissions)"
                        ),
                    ),
                    Text(text=_("Enter the user credentials below")),
                ],
                list_type="ordered",
            ),
            NoteText(
                text=_(
                    "Assuming your Proxmox username is 'checkmk', it needs to be configured as "
                    "'checkmk@pve' here"
                )
            ),
            FormSpecWrapper(
                id=FormSpecId("credentials"),
                form_spec=TwoColumnDictionary(
                    elements=proxmox_ve.credentials_elements(required=True),
                ),
            ),
            Collapsible(
                title=_("Advanced connection options"),
                items=[
                    NoteText(
                        text=_(
                            "Note: The 'IP address' option under 'Specify Proxmox VE host via...' "
                            "is not supported in the Quick Setup. Hosts created here have no "
                            "explicit IP address, so please use 'Host name' or 'Custom host' "
                            "instead."
                        )
                    ),
                    FormSpecWrapper(
                        id=FormSpecId("configure_advanced"),
                        form_spec=TwoColumnDictionary(
                            elements=proxmox_ve.connection_elements(),
                        ),
                    ),
                ],
            ),
        ],
        actions=[
            QuickSetupBackgroundStageAction(
                id=ActionId("action"),
                custom_validators=[
                    qs_validators.validate_non_quick_setup_password(
                        parameter_form=proxmox_ve.form_special_agents_proxmox_ve()
                    ),
                    qs_validators.validate_test_connection_custom_collect_params(
                        rulespec_name=RuleGroup.SpecialAgents("proxmox_ve"),
                        parameter_form=proxmox_ve.form_special_agents_proxmox_ve(),
                        custom_collect_params=_collect_params_for_connection_test,
                        error_message=_(
                            "Could not access your Proxmox VE account. Please check your "
                            "credentials."
                        ),
                    ),
                ],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Review and run connection test"),
                permissions=["wato.passwords"],
            )
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def _save_and_activate_recap(title: str) -> Sequence[Widget]:
    return [
        Text(text=title),
        Text(text=_("Save your progress and go to the Activate Changes page to enable it.")),
        NoteText(
            text=_(
                "We also recommend that you install Checkmk Linux agents on the Proxmox VE "
                "nodes — this will provide you with much more interesting information about your "
                "Proxmox VE environment."
            )
        ),
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
        rulespec_name=RuleGroup.SpecialAgents("proxmox_ve"),
        all_stages_form_data=parsed_data,
        parameter_form=proxmox_ve.form_special_agents_proxmox_ve(),
        collect_params=proxmox_ve_collect_params,
        progress_logger=progress_logger,
        site_configs=site_configs,
        debug=debug,
    )
    proxmox_ve_service_interest = ServiceInterest("proxmox_.*", "services")
    filtered_groups_of_services, _other_services = utils.group_services_by_interest(
        services_of_interest=[proxmox_ve_service_interest],
        service_discovery_result=service_discovery_result,
    )
    if len(filtered_groups_of_services[proxmox_ve_service_interest]):
        return _save_and_activate_recap(_("Proxmox VE services found!"))
    return [
        Text(text=_("No Proxmox VE services found.")),
        Text(
            text=_(
                "The connection to Proxmox VE was successful, but no services were found. This "
                "can be the case if your chosen host name does not match a node name within "
                "Proxmox VE. Otherwise, please verify your configuration."
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
                    lambda _a, _b, _parsed_data, *_args, **_kwargs: _save_and_activate_recap(
                        _("Skipped the configuration test.")
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
    _use_git: bool,
    _pprint_value: bool,
) -> str:
    match mode:
        case QuickSetupActionMode.SAVE:
            return complete.create_and_save_special_agent_bundle_custom_collect_params(
                special_agent_name="proxmox_ve",
                parameter_form=proxmox_ve.form_special_agents_proxmox_ve(),
                all_stages_form_data=all_stages_form_data,
                custom_collect_params=proxmox_ve_collect_params,
                progress_logger=progress_logger,
            )
        case QuickSetupActionMode.EDIT:
            raise ValueError("Edit mode not supported")
        case _:
            raise ValueError(f"Unknown mode {mode}")


def proxmox_ve_collect_params(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    return collect_params_from_form_data(all_stages_form_data, parameter_form)


quick_setup_proxmox_ve = QuickSetup(
    title=_("Proxmox VE"),
    id=QuickSetupId(RuleGroup.SpecialAgents("proxmox_ve")),
    stages=[
        configure_host,
        configure_authentication,
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
