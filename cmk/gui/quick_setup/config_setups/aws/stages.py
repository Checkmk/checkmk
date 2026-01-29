#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from livestatus import SiteConfiguration

from cmk.ccc.site import SiteId
from cmk.gui.form_specs.unstable.two_column_dictionary import TwoColumnDictionary
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.quick_setup.config_setups.aws import form_specs as aws
from cmk.gui.quick_setup.config_setups.aws.form_specs import quick_setup_aws_form_spec
from cmk.gui.quick_setup.v0_unstable.definitions import QSSiteSelection
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
from cmk.gui.utils.urls import doc_reference_url, DocReference, makeuri_contextless
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.utils.rulesets.definition import RuleGroup

NEXT_BUTTON_ARIA_LABEL = _("Go to the next stage")
PREV_BUTTON_ARIA_LABEL = _("Go to the previous stage")
PREV_BUTTON_LABEL = _("Back")


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
                text=_(
                    "Note: For access options like AssumeRole or a custom IAM region, please use "
                    "the %s."
                )
                % HTMLWriter.render_a(
                    _("advanced configuration"),
                    href=makeuri_contextless(
                        request,
                        [("mode", "edit_ruleset"), ("varname", "special_agents:aws")],
                        "wato.py",
                    ),
                )
            ),
            widgets.unique_id_formspec_wrapper(
                title=Title("Configuration name"), prefill_template="aws_config"
            ),
            FormSpecWrapper(
                id=FormSpecId("credentials"),
                form_spec=TwoColumnDictionary(
                    elements=aws.quick_setup_stage_1(),
                ),
            ),
        ],
        actions=[
            QuickSetupBackgroundStageAction(
                id=ActionId("connection_test"),
                custom_validators=[
                    qs_validators.validate_unique_id,
                    qs_validators.validate_non_quick_setup_password(
                        parameter_form=quick_setup_aws_form_spec()
                    ),
                    qs_validators.validate_test_connection_custom_collect_params(
                        rulespec_name=RuleGroup.SpecialAgents("aws"),
                        parameter_form=quick_setup_aws_form_spec(),
                        custom_collect_params=_collect_params_for_connection_test,
                        error_message=_(
                            "Could not access your AWS account. Please check your access and secret key and try again."
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
        configure_components=[
            widgets.host_name_and_host_path_formspec_wrapper(host_prefill_template="aws"),
            FormSpecWrapper(
                id=FormSpecId("configure_host_and_regions"),
                form_spec=TwoColumnDictionary(
                    elements=aws.quick_setup_stage_2(max_regions=5),
                ),
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


def _configure() -> Sequence[Widget]:
    return [
        FormSpecWrapper(
            id=FormSpecId("configure_services_to_monitor"),
            form_spec=TwoColumnDictionary(
                elements=aws.quick_setup_stage_3(),
                custom_validate=[],
            ),
        ),
        Collapsible(
            title="Other options",
            items=[
                FormSpecWrapper(
                    id=FormSpecId("aws_other_options"),
                    form_spec=TwoColumnDictionary(
                        elements={
                            **aws.formspec_aws_overall_tags(),
                        },
                    ),
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


class _CreateEC2:
    handle_automatically: bool = False


ec2_creation = _CreateEC2()


def _save_and_activate_recap(title: str, parsed_data: ParsedFormData) -> Sequence[Widget]:
    messages: list[Text | NoteText] = [
        Text(text=title),
        Text(text=_("Save your progress and go to the Activate Changes page to enable it.")),
    ]
    if "ec2" in parsed_data.get(FormSpecId("configure_services_to_monitor"), {}).get(
        "services", []
    ):
        if not ec2_creation.handle_automatically:
            messages.append(
                Text(
                    text=_(
                        "Hosts for EC2 instances need to be created manually, please check the %s."
                    )
                    % HTMLWriter.render_a(
                        _("documentation"),
                        href=doc_reference_url(DocReference.AWS_MANUAL_VM),
                    )
                )
            )
        else:
            messages.extend(
                [
                    Text(text=_("EC2 instances may take a few minutes to show up.")),
                    Text(),
                    NoteText(
                        text=_(
                            "Note: This will also enable the dynamic configuration, which regularly activates all pending changes on the selected site."
                        )
                    ),
                ]
            )
    return messages


def recap_found_services(
    _quick_setup_id: QuickSetupId,
    _stage_index: StageIndex,
    parsed_data: ParsedFormData,
    progress_logger: ProgressLogger,
    site_configs: Mapping[SiteId, SiteConfiguration],
    debug: bool,
) -> Sequence[Widget]:
    service_discovery_result = utils.get_service_discovery_preview(
        rulespec_name=RuleGroup.SpecialAgents("aws"),
        all_stages_form_data=parsed_data,
        parameter_form=quick_setup_aws_form_spec(),
        collect_params=aws_collect_params_with_defaults,
        progress_logger=progress_logger,
        site_configs=site_configs,
        debug=debug,
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
        return _save_and_activate_recap(_("AWS services found!"), parsed_data)
    return [
        Text(text=_("No AWS services found.")),
        Text(
            text=_(
                "The connection to AWS was successful, but no services were found. If this is unintentional, please verify your configuration."
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
                recap=[
                    recap_found_services,
                ],
                load_wait_label=_("This process may take several minutes, please wait..."),
                next_button_label=_("Test configuration"),
                target_site_formspec_key=QSSiteSelection,
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
                special_agent_name="aws",
                parameter_form=quick_setup_aws_form_spec(),
                all_stages_form_data=all_stages_form_data,
                custom_collect_params=aws_collect_params,
                progress_logger=progress_logger,
            )
        case QuickSetupActionMode.EDIT:
            raise ValueError("Edit mode not supported")
        case _:
            raise ValueError(f"Unknown mode {mode}")


def aws_collect_params(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    return aws_transform_to_disk(
        collect_params_from_form_data(all_stages_form_data, parameter_form)
    )


def aws_collect_params_with_defaults(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    return aws_transform_to_disk(
        collect_params_with_defaults_from_form_data(all_stages_form_data, parameter_form)
    )


def _collect_params_for_connection_test(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    """For the quick setup validation of the AWS authentication we run a connection test only using
    the agent option "--connection-test"."""
    return {
        **aws_transform_to_disk(
            collect_params_with_defaults_from_form_data(all_stages_form_data, parameter_form)
        ),
        "connection_test": True,
    }


def _migrate_aws_service(service: str) -> object:
    # Global
    if service in ["ce", "route53"]:
        return None
    if service == "cloudfront":
        return {"selection": "all", "host_assignment": "aws_host"}
    # Regional
    if service == "wafv2":
        return {"selection": "all", "limits": True, "cloudfront": None}
    if service == "cloudwatch_alarms":
        return {"alarms": "all", "limits": True}
    return {"selection": "all", "limits": True}


def aws_transform_to_disk(params: Mapping[str, object]) -> Mapping[str, object]:
    global_services = params["global_services"]
    assert isinstance(global_services, list)
    services = params["services"]
    assert isinstance(services, list)
    overall_tags = params.get("overall_tags")

    regions_to_monitor = params["regions_to_monitor"]
    assert isinstance(regions_to_monitor, list)
    keys_to_rename = {"aws_lambda": "lambda"}
    proxy_details = params.get("proxy_details")
    params = {
        "auth": (
            "access_key",
            {
                "access_key_id": params["access_key_id"],
                "secret_access_key": params["secret_access_key"],
            },
        ),
        "global_services": {k: _migrate_aws_service(k) for k in global_services},
        "regions": [region.replace("_", "-") for region in regions_to_monitor],
        "access": {},
        # TODO required key but not yet implemented. It's part of quick_setup_advanced()
        "regional_services": {keys_to_rename.get(k, k): _migrate_aws_service(k) for k in services},
        "piggyback_naming_convention": "ip_region_instance",
    }
    if proxy_details is not None:
        assert isinstance(proxy_details, dict)
        assert "proxy_host" in proxy_details
        params["proxy_details"] = proxy_details

    if overall_tags is not None:
        assert isinstance(overall_tags, dict)
        if (import_tags := overall_tags.get("import_tags")) is not None:
            assert isinstance(import_tags, tuple)
            params["import_tags"] = import_tags
        if (restriction_tags := overall_tags.get("restriction_tags")) is not None:
            assert isinstance(restriction_tags, list)
            params["overall_tags"] = [(tag["key"], tag["values"]) for tag in restriction_tags]

    return params


quick_setup_aws = QuickSetup(
    title=_("Amazon Web Services (AWS)"),
    id=QuickSetupId(RuleGroup.SpecialAgents("aws")),
    stages=[
        prepare_aws,
        configure_host_and_regions,
        configure_services_to_monitor,
        review_and_run_preview_service_discovery,
    ],
    actions=[
        QuickSetupBackgroundAction(
            id=ActionId("activate_changes"),
            label=_("Save & go to Activate changes"),
            action=action,
            icon=QuickSetupActionButtonIcon(name="save-to-services"),
            custom_validators=[qs_validators.validate_host_name_doesnt_exists],
            permissions=["wato.passwords", "wato.rulesets", "wato.hosts"],
        ),
    ],
)
