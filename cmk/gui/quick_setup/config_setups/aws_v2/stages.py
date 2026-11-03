#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Quick Setup of the new AWS integration.

Every field comes from the builders of the aws_v2 rule. The Quick Setup only arranges the
fields into stages, so that it stays the same as the rule.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace

from cmk.gui.form_specs.unstable.two_column_dictionary import TwoColumnDictionary
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.quick_setup.v0_unstable.definitions import QSSiteSelection
from cmk.gui.quick_setup.v0_unstable.predefined import (
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
    QuickSetupContext,
    QuickSetupStage,
    QuickSetupStageAction,
    StepStatus,
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
from cmk.plugins.aws_v2.rulesets import (  # astrein: disable=module-layers
    aws,
)
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.rulesets.v1 import Message, Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, validators
from cmk.web.utils.urls import makeuri_contextless

RULESET_NAME = RuleGroup.SpecialAgents("aws_v2")
PREV_BUTTON_LABEL = _("Back")
MAX_REGIONS = 5


def _access_options() -> Mapping[str, DictElement[object]]:
    # The rule selects the authentication in "auth". The Quick Setup only offers the access
    # key, see _rule_value().
    return {
        key: element for key, element in aws.configuration_authentication().items() if key != "auth"
    }


def _regions() -> Mapping[str, DictElement[object]]:
    regions = aws.configuration_regions_and_tags()["regions"]
    return {
        "regions": replace(
            regions,
            parameter_form=replace(
                regions.parameter_form,
                custom_validate=(
                    *(regions.parameter_form.custom_validate or ()),
                    validators.LengthInRange(
                        max_value=MAX_REGIONS,
                        error_msg=Message("Please select at most %(max_regions)s regions.")
                        % {"max_regions": str(MAX_REGIONS)},
                    ),
                ),
            ),
        )
    }


def _other_options() -> Mapping[str, DictElement[object]]:
    return {
        **{
            key: element
            for key, element in aws.configuration_regions_and_tags().items()
            if key != "regions"
        },
        **aws.configuration_piggyback_naming(),
    }


def quick_setup_formspec() -> Dictionary:
    """All fields of the Quick Setup, as the stages put them on the first level"""
    return Dictionary(
        elements={
            **aws.configuration_access_key(),
            **_access_options(),
            **_regions(),
            **aws.configuration_services(),
            **_other_options(),
        }
    )


def prepare_aws() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Prepare AWS for Checkmk"),
        configure_components=[
            ListOfWidgets(
                items=[
                    Text(text=_("Go to AWS root account > Services > IAM.")),
                    Text(
                        text=_(
                            'Click "Add user" under Users, select "Access key - Programmatic '
                            'access", and attach the "ReadOnlyAccess" policy.',
                        ),
                        tooltip=_(
                            "Since this is a ReadOnlyAccess, we won't create any resources on "
                            "your AWS account."
                        ),
                    ),
                    Text(text=_("Note down the generated access key ID and secret access key.")),
                    Text(
                        text=_(
                            "Return to Checkmk, define a unique configuration name, and use the "
                            "access key ID and secret access key below."
                        )
                    ),
                ],
                list_type="ordered",
            ),
            NoteText(
                text=_("Note: To authenticate with an IAM role, please use the %(link)s.")
                % {
                    "link": HTMLWriter.render_a(
                        _("advanced configuration"),
                        href=makeuri_contextless(
                            request,
                            [("mode", "edit_ruleset"), ("varname", RULESET_NAME)],
                            "wato.py",
                        ),
                    )
                }
            ),
            widgets.unique_id_formspec_wrapper(
                title=Title("Configuration name"), prefill_template="aws_config"
            ),
            FormSpecWrapper(
                id=FormSpecId("credentials"),
                form_spec=TwoColumnDictionary(elements=aws.configuration_access_key()),
            ),
            Collapsible(
                title=_("Other options"),
                items=[
                    FormSpecWrapper(
                        id=FormSpecId("access_options"),
                        form_spec=TwoColumnDictionary(elements=_access_options()),
                    ),
                ],
            ),
        ],
        actions=[
            QuickSetupBackgroundStageAction(
                id=ActionId("connection_test"),
                custom_validators=[
                    qs_validators.validate_unique_id,
                    qs_validators.validate_non_quick_setup_password(
                        parameter_form=quick_setup_formspec()
                    ),
                    qs_validators.validate_test_connection_custom_collect_params(
                        rulespec_name=RULESET_NAME,
                        parameter_form=quick_setup_formspec(),
                        custom_collect_params=_collect_params_for_connection_test,
                        error_message=_(
                            "Could not access your AWS account. Please check your access and "
                            "secret key and try again."
                        ),
                    ),
                ],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Configure host and regions"),
                permissions=["wato.passwords"],
            )
        ],
    )


def configure_host_and_regions() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure host and regions"),
        sub_title=_(
            "Name your host, define the path and select the regions you would like to monitor"
        ),
        configure_components=lambda ctx: [
            widgets.host_name_and_host_path_formspec_wrapper(
                ctx.tree, ctx.user, host_prefill_template="aws"
            ),
            FormSpecWrapper(
                id=FormSpecId("configure_regions"),
                form_spec=TwoColumnDictionary(elements=_regions()),
            ),
            widgets.site_formspec_wrapper(),
        ],
        actions=[
            QuickSetupStageAction(
                id=ActionId("host_name"),
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


def _configure_services(_ctx: QuickSetupContext) -> Sequence[Widget]:
    return [
        FormSpecWrapper(
            id=FormSpecId("configure_services_to_monitor"),
            form_spec=TwoColumnDictionary(elements=aws.configuration_services()),
        ),
        Collapsible(
            title=_("Other options"),
            items=[
                FormSpecWrapper(
                    id=FormSpecId("aws_other_options"),
                    form_spec=TwoColumnDictionary(elements=_other_options()),
                ),
            ],
        ),
    ]


def configure_services_to_monitor() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure services to monitor & other options"),
        sub_title=_(
            "Select and configure AWS services you would like to monitor, "
            "and optionally restrict them with AWS tags."
        ),
        configure_components=_configure_services,
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Review and test configuration"),
            )
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def _save_and_activate_recap(title: str) -> Sequence[Widget]:
    return [
        Text(text=title),
        Text(text=_("Save your progress and go to the 'Activate changes' page to enable it.")),
    ]


def recap_found_services(
    _quick_setup_id: QuickSetupId,
    _stage_index: StageIndex,
    parsed_data: ParsedFormData,
    progress_logger: ProgressLogger,
    ctx: QuickSetupContext,
) -> Sequence[Widget]:
    service_discovery_result = utils.get_service_discovery_preview(
        rulespec_name=RULESET_NAME,
        all_stages_form_data=parsed_data,
        parameter_form=quick_setup_formspec(),
        collect_params=collect_params,
        progress_logger=progress_logger,
        site_configs=ctx.site_configs,
        debug=ctx.debug,
    )
    progress_logger.log_new_progress_step(
        "identify_relevant_services", "Search for AWS related services"
    )
    aws_service_interest = ServiceInterest(r"(?i).*aws.*", "services")
    filtered_groups_of_services, _other_services = utils.group_services_by_interest(
        services_of_interest=[aws_service_interest],
        service_discovery_result=service_discovery_result,
    )
    progress_logger.update_progress_step_status("identify_relevant_services", StepStatus.COMPLETED)
    if len(filtered_groups_of_services[aws_service_interest]):
        return _save_and_activate_recap(_("AWS services found!"))
    return [
        Text(text=_("No AWS services found.")),
        Text(
            text=_(
                "The connection to AWS was successful, but no services were found. If this is "
                "unintentional, please verify your configuration."
            )
        ),
    ]


def review_and_run_preview_service_discovery() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Review and test configuration"),
        sub_title=_("Test the AWS connection based on your configuration settings."),
        configure_components=[],
        actions=[
            QuickSetupBackgroundStageAction(
                id=ActionId("action"),
                custom_validators=[],
                recap=[recap_found_services],
                load_wait_label=_("This process may take several minutes, please wait..."),
                next_button_label=_("Test configuration"),
                target_site_formspec_key=QSSiteSelection,
            ),
            QuickSetupStageAction(
                id=ActionId("skip_configuration_test"),
                custom_validators=[],
                recap=[
                    lambda *args, **kwargs: _save_and_activate_recap(  # noqa: ARG005
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
    ctx: QuickSetupContext,
) -> str:
    match mode:
        case QuickSetupActionMode.SAVE:
            return complete.create_and_save_special_agent_bundle_custom_collect_params(
                special_agent_name="aws_v2",
                parameter_form=quick_setup_formspec(),
                all_stages_form_data=all_stages_form_data,
                custom_collect_params=collect_params,
                progress_logger=progress_logger,
                tree=ctx.tree,
            )
        case QuickSetupActionMode.EDIT:
            raise ValueError("Edit mode not supported")
        case _:
            raise ValueError(f"Unknown mode {mode}")


def _rule_value(params: Mapping[str, object]) -> Mapping[str, object]:
    # The Quick Setup keeps the access key on the first level, where the Quick Setup handles
    # the password. The rule expects it as the selected authentication.
    access_key_fields = aws.configuration_access_key()
    return {
        "auth": (
            "access_key",
            {**{key: params[key] for key in access_key_fields}, "accounts": ("single", None)},
        ),
        **{key: value for key, value in params.items() if key not in access_key_fields},
    }


def collect_params(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    """Return the value of the rule that the Quick Setup creates"""
    return _rule_value(
        collect_params_with_defaults_from_form_data(all_stages_form_data, parameter_form)
    )


def _collect_params_for_connection_test(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    # The agent option "--connection-test" only tests the access to AWS.
    return {**collect_params(all_stages_form_data, parameter_form), "connection_test": True}


quick_setup_aws_v2 = QuickSetup(
    title=_("Amazon Web Services (AWS) v2"),
    id=QuickSetupId(RULESET_NAME),
    stages=[
        prepare_aws,
        configure_host_and_regions,
        configure_services_to_monitor,
        review_and_run_preview_service_discovery,
    ],
    actions=[
        QuickSetupBackgroundAction(
            id=ActionId("activate_changes"),
            label=_("Save & go to 'Activate changes'"),
            action=action,
            icon=QuickSetupActionButtonIcon(name="save-to-services"),
            custom_validators=[qs_validators.validate_host_name_doesnt_exists],
            permissions=["wato.passwords", "wato.rulesets", "wato.hosts"],
        ),
    ],
)
