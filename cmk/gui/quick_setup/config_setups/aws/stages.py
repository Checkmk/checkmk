#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.ccc.i18n import _

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.form_specs.private.dictionary_extended import DictionaryExtended
from cmk.gui.form_specs.vue.shared_type_defs import DictionaryLayout
from cmk.gui.quick_setup.config_setups.aws import form_specs as aws
from cmk.gui.quick_setup.config_setups.aws import ruleset_helper
from cmk.gui.quick_setup.config_setups.aws.form_specs import quick_setup_aws_form_spec
from cmk.gui.quick_setup.v0_unstable.definitions import QSSiteSelection
from cmk.gui.quick_setup.v0_unstable.predefined import (
    collect_params_from_form_data,
    complete,
    recaps,
    widgets,
)
from cmk.gui.quick_setup.v0_unstable.predefined import validators as qs_validators
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetup, QuickSetupSaveAction, QuickSetupStage
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
    Dictionary,
    InputHint,
    SingleChoice,
    SingleChoiceElement,
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
                    Text(text=_("Note down the generated Access key ID and Secret access key.")),
                    Text(
                        text=_(
                            "Return to Checkmk, define a unique AWS account name, and use the "
                            "Access key ID and Secret access key below."
                        )
                    ),
                ],
                list_type="ordered",
            ),
            widgets.unique_id_formspec_wrapper(
                title=Title("Configuration name"), prefill_template="aws_config"
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
    site_default_value = site_attribute_default_value()
    return QuickSetupStage(
        title=_("Configure host and regions"),
        sub_title=_(
            "Name your host, define the path and select the regions you would like to monitor"
        ),
        configure_components=[
            widgets.host_name_and_host_path_formspec_wrapper(host_prefill_template="aws"),
            FormSpecWrapper(
                id=FormSpecId("configure_host_and_regions"),
                form_spec=DictionaryExtended(
                    elements=aws.quick_setup_stage_2(),
                    layout=DictionaryLayout.two_columns,
                ),
            ),
            FormSpecWrapper(
                id=FormSpecId("site"),
                form_spec=DictionaryExtended(
                    elements={
                        QSSiteSelection: DictElement(
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
        ],
        custom_validators=[qs_validators.validate_host_name_doesnt_exists],
        recap=[recaps.recaps_form_spec],
        button_label="Configure services to monitor",
    )


def _configure() -> Sequence[Widget]:
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
                rulespec_name=RuleGroup.SpecialAgents("aws"),
                parameter_form=quick_setup_aws_form_spec(),
                custom_collect_params=aws_collect_params,
            )
        ],
        recap=[
            recaps.recap_service_discovery_custom_collect_params(
                rulespec_name=RuleGroup.SpecialAgents("aws"),
                parameter_form=quick_setup_aws_form_spec(),
                services_of_interest=[ServiceInterest(".*", "services")],
                custom_collect_params=aws_collect_params,
            )
        ],
        button_label="Run preview service discovery",
    )


def save_action(all_stages_form_data: ParsedFormData) -> str:
    return complete.create_and_save_special_agent_bundle_custom_collect_params(
        special_agent_name="aws",
        parameter_form=quick_setup_aws_form_spec(),
        all_stages_form_data=all_stages_form_data,
        custom_collect_params=aws_collect_params,
    )


def aws_collect_params(
    all_stages_form_data: ParsedFormData, parameter_form: Dictionary
) -> Mapping[str, object]:
    return aws_transform_to_disk(
        collect_params_from_form_data(all_stages_form_data, parameter_form)
    )


def _migrate_aws_service(service: str) -> object:
    # Global
    if service in ["ce", "route53"]:
        return None
    if service == "cloudfront":
        return {"selection": "all", "host_assignment": "aws_host"}
    # Regional
    if service == "wafv2":
        return {"selection": "all", "limits": True, "cloudfront": None}
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
    params = {
        "access_key_id": params["access_key_id"],
        "secret_access_key": params["secret_access_key"],
        "global_services": {k: _migrate_aws_service(k) for k in global_services},
        "regions": [region.replace("_", "-") for region in regions_to_monitor],
        "access": {},  # TODO required key but not yet implemented. It's part of quick_setup_advanced()
        "services": {keys_to_rename.get(k, k): _migrate_aws_service(k) for k in services},
        "piggyback_naming_convention": "ip_region_instance",
    }
    if overall_tags is not None:
        assert isinstance(overall_tags, list)
        params["overall_tags"] = [(tag["key"], tag["values"]) for tag in overall_tags]

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
    save_actions=[
        QuickSetupSaveAction(
            id="activate_changes",
            label=_("Save & go to Activate changes"),
            action=save_action,
        ),
    ],
)
