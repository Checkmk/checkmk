#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.quick_setup.definitions import QuickSetup, QuickSetupId, QuickSetupStage, StageId
from cmk.gui.quick_setup.widgets import FormSpecWrapper, List, NoteText

from cmk.ccc.i18n import _
from cmk.plugins.aws.rulesets import aws  # pylint: disable=cmk-module-layer-violation
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, FieldSize, String, validators


def prepare_aws(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Prepare AWS for Checkmk"),
        components=[
            List(
                items=[
                    _("Go to AWS root account > Services > IAM."),
                    _(
                        "Click 'Add user' under Users, select 'Access key - Programmatic access', and attach the 'ReadOnlyAccess' policy*."
                    ),
                    _("Save the generated access key and secret key for later use."),
                ]
            ),
            FormSpecWrapper(
                id="aws_account_name",
                form_spec=Dictionary(
                    elements={
                        "account_name": DictElement(
                            parameter_form=String(
                                title=Title("AWS account name"),
                                field_size=FieldSize.MEDIUM,
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                            required=True,
                        )
                    }
                ),
            ),
            NoteText(
                text=_(
                    "*Since this is a ReadOnlyAccess, we will never create any resources on your AWS account"
                )
            ),
            FormSpecWrapper(
                id="credentials",
                form_spec=Dictionary(elements=aws.quick_setup_stage_1()),
            ),
        ],
    )


def configure_host_and_region(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Configure host and regions"),
        sub_title=_(
            "Name your host, define the path and select the regions you would like to monitor"
        ),
        components=[
            FormSpecWrapper(
                id="configure_host_and_region",
                form_spec=Dictionary(elements=aws.quick_setup_stage_2()),
            ),
        ],
    )


def configure_services_to_monitor(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Configure services to monitor"),
        sub_title=_("Select and configure AWS services you would like to monitor"),
        components=[],
    )


def review_and_run_service_discovery(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Review and run service discovery"),
        sub_title=_("Review your configuration, run and preview service discovery"),
        components=[],
    )


def aws_stages() -> Sequence[QuickSetupStage]:
    return [
        prepare_aws(StageId(1)),
        configure_host_and_region(StageId(2)),
        configure_services_to_monitor(StageId(3)),
        review_and_run_service_discovery(StageId(4)),
    ]


aws_quicksetup = QuickSetup(
    id=QuickSetupId("aws_quick_setup"),
    stages=aws_stages(),
)
