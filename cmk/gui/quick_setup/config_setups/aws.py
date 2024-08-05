#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.quick_setup.predefined import unique_id_formspec_wrapper
from cmk.gui.quick_setup.to_frontend import (
    create_and_save_special_agent_bundle,
    recap_service_discovery,
    recaps_form_spec,
    validate_test_connection,
    validate_unique_id,
)
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetup, QuickSetupStage
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ParsedFormData,
    QuickSetupId,
    ServiceInterest,
    StageId,
)
from cmk.gui.quick_setup.v0_unstable.widgets import (
    Collapsible,
    FormSpecId,
    FormSpecWrapper,
    ListOfWidgets,
    Text,
)

from cmk.ccc.i18n import _
from cmk.plugins.aws import ruleset_helper  # pylint: disable=cmk-module-layer-violation
from cmk.plugins.aws.rulesets import aws  # pylint: disable=cmk-module-layer-violation
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, FieldSize, String, validators


def prepare_aws(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Prepare AWS for Checkmk"),
        configure_components=[
            ListOfWidgets(
                items=[
                    Text(
                        text=_("Go to AWS root account > Services > IAM."),
                    ),
                    Text(
                        text=_(
                            "Click 'Add user' under Users, select 'Access key - Programmatic access', and attach the 'ReadOnlyAccess' policy."
                        ),
                    ),
                    Text(
                        text=_("Save the generated access key and secret key for later use."),
                        tooltip="Since this is a ReadOnlyAccess, we won't create any resources on your AWS account",
                    ),
                ],
                list_type="ordered",
            ),
            unique_id_formspec_wrapper(
                title=Title("AWS account name"), prefill_template="aws_config"
            ),
            FormSpecWrapper(
                id=FormSpecId("credentials"),
                form_spec=Dictionary(elements=aws.quick_setup_stage_1()),
            ),
        ],
        validators=[validate_unique_id],
        recap=[recaps_form_spec],
        button_label="Configure host and region",
    )


def configure_host_and_region(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Configure host and regions"),
        sub_title=_(
            "Name your host, define the path and select the regions you would like to monitor"
        ),
        configure_components=[
            FormSpecWrapper(
                id=FormSpecId("host_data"),
                form_spec=Dictionary(
                    elements={
                        "host_name": DictElement(
                            parameter_form=String(
                                title=Title("Host name"),
                                field_size=FieldSize.MEDIUM,
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                            required=True,
                        ),
                        "host_path": DictElement(
                            parameter_form=String(
                                title=Title("Host path"),
                                field_size=FieldSize.MEDIUM,
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                            required=True,
                        ),
                    }
                ),
            ),
            FormSpecWrapper(
                id=FormSpecId("configure_host_and_region"),
                form_spec=Dictionary(elements=aws.quick_setup_stage_2()),
            ),
        ],
        validators=[],
        recap=[recaps_form_spec],
        button_label="Configure services to monitor",
    )


def configure_services_to_monitor(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Configure services to monitor"),
        sub_title=_("Select and configure AWS services you would like to monitor"),
        configure_components=[
            FormSpecWrapper(
                id=FormSpecId("configure_services_to_monitor"),
                form_spec=Dictionary(elements=aws.quick_setup_stage_3()),
            ),
            Collapsible(
                title="Other options",
                items=[
                    FormSpecWrapper(  # TODO Placeholder for site selection
                        id=FormSpecId("site"),
                        form_spec=Dictionary(
                            elements={
                                "site_selection": DictElement(
                                    parameter_form=String(
                                        title=Title("Site selection"),
                                        field_size=FieldSize.MEDIUM,
                                    ),
                                    required=True,
                                ),
                            }
                        ),
                    ),
                    FormSpecWrapper(
                        id=FormSpecId("aws_tags"),
                        form_spec=Dictionary(
                            elements={
                                "overall_tags": DictElement(
                                    parameter_form=ruleset_helper.formspec_aws_tags(
                                        Title(
                                            "Restrict monitoring services by one of these AWS tags"
                                        )
                                    ),
                                ),
                            },
                        ),
                    ),
                ],
            ),
        ],
        validators=[
            # TODO: move to correct location
            validate_test_connection(RuleGroup.SpecialAgents("aws")),
        ],
        recap=[
            recaps_form_spec,
            # TODO: move to correct location and add correct services_of_interest
            recap_service_discovery(
                RuleGroup.SpecialAgents("aws"),
                [ServiceInterest(".*", "services")],
            ),
        ],
        button_label="Review and run service discovery",
    )


def review_and_run_service_discovery(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Review and run service discovery"),
        sub_title=_("Review your configuration, run and preview service discovery"),
        configure_components=[],
        validators=[],
        recap=[],
        button_label="Run & preview service discovery",
    )


def aws_stages() -> Sequence[QuickSetupStage]:
    return [
        prepare_aws(StageId(1)),
        configure_host_and_region(StageId(2)),
        configure_services_to_monitor(StageId(3)),
        review_and_run_service_discovery(StageId(4)),
    ]


def save_action(all_stages_form_data: ParsedFormData) -> str:
    return create_and_save_special_agent_bundle(
        special_agent_name="aws",
        all_stages_form_data=all_stages_form_data,
    )


quick_setup_aws = QuickSetup(
    title=_("Amazon Web Services (AWS)"),
    id=QuickSetupId("aws_quick_setup"),
    stages=aws_stages(),
    save_action=save_action,
    button_complete_label=_("Save & go to Activate changes"),
)
