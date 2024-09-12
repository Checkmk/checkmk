#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.ccc.i18n import _

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.fields.definitions import FOLDER_PATTERN
from cmk.gui.form_specs.private.dictionary_extended import DictionaryExtended
from cmk.gui.form_specs.vue.shared_type_defs import DictionaryLayout
from cmk.gui.quick_setup.config_setups.aws import form_specs as aws
from cmk.gui.quick_setup.config_setups.aws import ruleset_helper
from cmk.gui.quick_setup.v0_unstable.predefined import (
    collect_params_from_form_data,
    complete,
    recaps,
    widgets,
)
from cmk.gui.quick_setup.v0_unstable.predefined import validators as qs_validators
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetup, QuickSetupStage
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData, QuickSetupId, ServiceInterest
from cmk.gui.quick_setup.v0_unstable.widgets import (
    Collapsible,
    FormSpecId,
    FormSpecWrapper,
    ListOfWidgets,
    Text,
    Widget,
)
from cmk.gui.user_sites import get_configured_site_choices, site_attribute_default_value

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
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
                    Text(text=_("Save the generated Access key and Secret access key.")),
                    Text(
                        text=_(
                            "Return to Checkmk, define a unique AWS account name, and use the "
                            "Access key and Secret access key below."
                        )
                    ),
                ],
                list_type="ordered",
            ),
            widgets.unique_id_formspec_wrapper(
                title=Title("AWS account name"), prefill_template="aws_config"
            ),
            FormSpecWrapper(
                id=FormSpecId("credentials"),
                form_spec=DictionaryExtended(
                    elements=aws.quick_setup_stage_1(),
                    layout=DictionaryLayout.two_columns,
                ),
            ),
        ],
        custom_validators=[qs_validators.validate_unique_id],
        recap=[recaps.recaps_form_spec],
        button_label="Configure host and regions",
    )


def configure_host_and_regions() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Configure host and regions"),
        sub_title=_(
            "Name your host, define the path and select the regions you would like to monitor"
        ),
        configure_components=[
            FormSpecWrapper(
                id=FormSpecId("host_data"),
                form_spec=DictionaryExtended(
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
                                custom_validate=(
                                    validators.LengthInRange(min_value=1),
                                    validators.MatchRegex(FOLDER_PATTERN),
                                ),
                            ),
                            required=True,
                        ),
                    },
                    layout=DictionaryLayout.two_columns,
                ),
            ),
            FormSpecWrapper(
                id=FormSpecId("configure_host_and_regions"),
                form_spec=DictionaryExtended(
                    elements=aws.quick_setup_stage_2(),
                    layout=DictionaryLayout.two_columns,
                ),
            ),
        ],
        custom_validators=[],
        recap=[recaps.recaps_form_spec],
        button_label="Configure services to monitor",
    )


def _configure() -> Sequence[Widget]:
    site_default_value = site_attribute_default_value()
    return [
        FormSpecWrapper(
            id=FormSpecId("configure_services_to_monitor"),
            form_spec=DictionaryExtended(
                elements=aws.quick_setup_stage_3(),
                layout=DictionaryLayout.two_columns,
            ),
        ),
        Collapsible(
            title="Other options",
            items=[
                FormSpecWrapper(
                    id=FormSpecId("site"),
                    form_spec=DictionaryExtended(
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
                                    title=Title("Site selection"),
                                    prefill=(
                                        DefaultValue(site_default_value)
                                        if site_default_value
                                        else InputHint(Title("Please choose"))
                                    ),
                                ),
                                required=True,
                            )
                        },
                        layout=DictionaryLayout.two_columns,
                    ),
                ),
                FormSpecWrapper(
                    id=FormSpecId("aws_tags"),
                    form_spec=DictionaryExtended(
                        elements={
                            "overall_tags": DictElement(
                                parameter_form=ruleset_helper.formspec_aws_tags(
                                    Title("Restrict monitoring services by one of these AWS tags")
                                ),
                            ),
                        },
                        layout=DictionaryLayout.two_columns,
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
            recaps.recaps_form_spec,
        ],
        button_label="Review & run preview service discovery",
    )


def review_and_run_preview_service_discovery() -> QuickSetupStage:
    return QuickSetupStage(
        title=_("Review and run preview service discovery"),
        sub_title=_("Review your configuration and run preview service discovery"),
        configure_components=[],
        custom_validators=[
            qs_validators.validate_test_connection_custom_collect_params(
                RuleGroup.SpecialAgents("aws"), custom_collect_params=aws_collect_params
            )
        ],
        recap=[
            recaps.recap_service_discovery_custom_collect_params(
                RuleGroup.SpecialAgents("aws"),
                [ServiceInterest(".*", "services")],
                custom_collect_params=aws_collect_params,
            )
        ],
        button_label="Run preview service discovery",
    )


def save_action(all_stages_form_data: ParsedFormData) -> str:
    return complete.create_and_save_special_agent_bundle_custom_collect_params(
        special_agent_name="aws",
        all_stages_form_data=all_stages_form_data,
        custom_collect_params=aws_collect_params,
    )


def aws_collect_params(
    all_stages_form_data: ParsedFormData, rulespec_name: str
) -> Mapping[str, object]:
    return aws_transform_to_disk(collect_params_from_form_data(all_stages_form_data, rulespec_name))


def _aws_service_defaults(service: str) -> tuple[str, dict | None]:
    if service in ["ce", "route53"]:
        return "all", {}
    if service == "cloudfront":
        return "all", {"host_assignment": "aws_host"}
    return "all", {"limits": "limits"}


def aws_transform_to_disk(params: Mapping[str, object]) -> Mapping[str, object]:
    global_services = params["global_services"]
    assert isinstance(global_services, list)
    services = params["services"]
    assert isinstance(services, list)
    overall_tags = params.get("overall_tags", [])
    assert isinstance(overall_tags, list)
    return {
        "access_key_id": params["access_key_id"],
        "secret_access_key": params["secret_access_key"],
        "access": {},
        "global_services": {k: _aws_service_defaults(k) for k in global_services},
        "regions_to_monitor": params["regions_to_monitor"],
        "services": {k: _aws_service_defaults(k) for k in services},
        "piggyback_naming_convention": "ip_region_instance",
        "overall_tags": overall_tags,
    }


quick_setup_aws = QuickSetup(
    title=_("Amazon Web Services (AWS)"),
    id=QuickSetupId(RuleGroup.SpecialAgents("aws")),
    stages=[
        prepare_aws(),
        configure_host_and_regions(),
        configure_services_to_monitor(),
        review_and_run_preview_service_discovery(),
    ],
    save_action=save_action,
    button_complete_label=_("Save & go to Activate changes"),
)
