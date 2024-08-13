#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Sequence

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
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData, QuickSetupId, ServiceInterest
from cmk.gui.quick_setup.v0_unstable.widgets import (
    Collapsible,
    FormSpecDictWrapper,
    FormSpecId,
    ListOfWidgets,
    Text,
    Widget,
)
from cmk.gui.user_sites import get_configured_site_choices, site_attribute_default_value

from cmk.ccc.i18n import _
from cmk.plugins.aws import ruleset_helper  # pylint: disable=cmk-module-layer-violation
from cmk.plugins.aws.rulesets import aws  # pylint: disable=cmk-module-layer-violation
from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    InputHint,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)


def prepare_aws() -> QuickSetupStage:
    return QuickSetupStage(
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
            FormSpecDictWrapper(
                id=FormSpecId("credentials"),
                form_spec=Dictionary(elements=aws.quick_setup_stage_1()),
                rendering_option="table",
            ),
        ],
        custom_validators=[validate_unique_id],
        recap=[recaps_form_spec],
        button_label="Configure host and region",
    )


def configure_host_and_region() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure host and regions"),
        sub_title=_(
            "Name your host, define the path and select the regions you would like to monitor"
        ),
        configure_components=[
            FormSpecDictWrapper(
                id=FormSpecId("host_data"),
                rendering_option="table",
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
            FormSpecDictWrapper(
                id=FormSpecId("configure_host_and_region"),
                rendering_option="table",
                form_spec=Dictionary(elements=aws.quick_setup_stage_2()),
            ),
        ],
        custom_validators=[],
        recap=[recaps_form_spec],
        button_label="Configure services to monitor",
    )


def _configure() -> Sequence[Widget]:
    site_default_value = site_attribute_default_value()
    return [
        FormSpecDictWrapper(
            id=FormSpecId("configure_services_to_monitor"),
            rendering_option="table",
            form_spec=Dictionary(elements=aws.quick_setup_stage_3()),
        ),
        Collapsible(
            title="Other options",
            items=[
                FormSpecDictWrapper(
                    id=FormSpecId("site"),
                    rendering_option="table",
                    form_spec=Dictionary(
                        elements={
                            "site_selection": DictElement(
                                parameter_form=SingleChoice(
                                    elements=[
                                        SingleChoiceElement(
                                            name=site_id,
                                            title=Title(  # pylint: disable=localization-of-non-literal-string
                                                title
                                            ),
                                        )
                                        for site_id, title in get_configured_site_choices()
                                    ],
                                    label=Label("Site selection"),
                                    prefill=(
                                        DefaultValue(site_default_value)
                                        if site_default_value
                                        else InputHint(Title("Please choose"))
                                    ),
                                ),
                                required=True,
                            )
                        }
                    ),
                ),
                FormSpecDictWrapper(
                    id=FormSpecId("aws_tags"),
                    rendering_option="table",
                    form_spec=Dictionary(
                        elements={
                            "overall_tags": DictElement(
                                parameter_form=ruleset_helper.formspec_aws_tags(
                                    Title("Restrict monitoring services by one of these AWS tags")
                                ),
                            ),
                        },
                    ),
                ),
            ],
        ),
    ]


def configure_services_to_monitor() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure services to monitor"),
        sub_title=_("Select and configure AWS services you would like to monitor"),
        configure_components=_configure,
        custom_validators=[],
        recap=[
            recaps_form_spec,
        ],
        button_label="Review and run service discovery",
    )


def review_and_run_service_discovery() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Review and run service discovery"),
        sub_title=_("Review your configuration, run and preview service discovery"),
        configure_components=[],
        custom_validators=[validate_test_connection(RuleGroup.SpecialAgents("aws"))],
        recap=[
            recap_service_discovery(
                RuleGroup.SpecialAgents("aws"),
                [ServiceInterest(".*", "services")],
            )
        ],
        button_label="Run preview service discovery",
    )


def save_action(all_stages_form_data: ParsedFormData) -> str:
    return create_and_save_special_agent_bundle(
        special_agent_name="aws",
        all_stages_form_data=all_stages_form_data,
    )


quick_setup_aws = QuickSetup(
    title=_("Amazon Web Services (AWS)"),
    id=QuickSetupId(RuleGroup.SpecialAgents("aws")),
    stages=[
        prepare_aws(),
        configure_host_and_region(),
        configure_services_to_monitor(),
        review_and_run_service_discovery(),
    ],
    save_action=save_action,
    button_complete_label=_("Save & go to Activate changes"),
)
