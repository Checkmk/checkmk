#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.plugins.aws.lib import aws_region_to_monitor
from cmk.plugins.aws.ruleset_helper import (
    convert_tag_list,
    formspec_aws_limits,
    formspec_aws_tags,
    migrate_regional_service,
    service_dict_element,
)

try:
    # Ignore import-untyped for non-CCE CI stages
    from cmk.plugins.aws.rulesets.cce import (  # type: ignore[import-untyped,unused-ignore]
        edition_specific_global_services,
        edition_specific_regional_services,
        handle_edition_switch,
        migrate_edition_specific_global_services_vs_to_fs,
        migrate_edition_specific_regional_services_vs_to_fs,
    )
except ImportError:
    from cmk.plugins.aws.rulesets.cre import (
        edition_specific_global_services,
        edition_specific_regional_services,
        migrate_edition_specific_global_services_vs_to_fs,
        migrate_edition_specific_regional_services_vs_to_fs,
        handle_edition_switch,
    )

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    Integer,
    migrate_to_password,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _global_services() -> dict[str, DictElement]:
    return {
        "ce": service_dict_element(
            Title("Costs and usage (CE)"),
            {},
            default_enabled=False,
            filterable_by_name=False,
            filterable_by_tags=False,
        ),
        **edition_specific_global_services(),
    }


def _regional_services() -> dict[str, DictElement]:
    return {
        "ec2": service_dict_element(
            Title("Elastic Compute Cloud (EC2)"), extra_elements=formspec_aws_limits()
        ),
        "ebs": service_dict_element(
            Title("Elastic Block Storage (EBS)"), extra_elements=formspec_aws_limits()
        ),
        "s3": service_dict_element(
            Title("Simple Storage Service (S3)"),
            {
                **formspec_aws_limits(),
                "requests": DictElement(
                    parameter_form=FixedValue(
                        value=None,
                        title=Title("Request metrics"),
                        label=Label(
                            "Monitor request metrics using the filter <tt>EntireBucket</tt>"
                        ),
                        help_text=Help(
                            "In order to monitor S3 request metrics, you have to enable "
                            "request metrics in the AWS/S3 console, see the "
                            "<a href='https://docs.aws.amazon.com/AmazonS3/latest/userguide/metrics-configurations.html'>AWS/S3 documentation</a>. "
                            "This is a paid feature. Note that the filter name has to be "
                            "set to <tt>EntireBucket</tt>, as is recommended in the "
                            "<a href='https://docs.aws.amazon.com/AmazonS3/latest/userguide/configure-request-metrics-bucket.html'>documentation for a filter that applies to all objects</a>. "
                            "The special agent will use this filter name to query S3 request "
                            "metrics from the AWS API."
                        ),
                    )
                ),
            },
        ),
        "glacier": service_dict_element(
            Title("Amazon S3 Glacier (Glacier)"), extra_elements=formspec_aws_limits()
        ),
        "elb": service_dict_element(
            Title("Classic Load Balancing (ELB)"), extra_elements=formspec_aws_limits()
        ),
        "elbv2": service_dict_element(
            Title("Application and Network Load Balancing (ELBv2)"),
            extra_elements=formspec_aws_limits(),
        ),
        "rds": service_dict_element(
            Title("Relational Database Service (RDS)"), extra_elements=formspec_aws_limits()
        ),
        "cloudwatch_alarms": service_dict_element(
            Title("CloudWatch Alarms"), formspec_aws_limits(), filterable_by_tags=False
        ),
        "dynamodb": service_dict_element(Title("DynamoDB"), extra_elements=formspec_aws_limits()),
        "wafv2": service_dict_element(
            Title("Web Application Firewall (WAFV2)"),
            extra_elements={
                **formspec_aws_limits(),
                "cloudfront": DictElement(
                    parameter_form=FixedValue(
                        title=Title("CloudFront WAFs"),
                        label=Label("Monitor CloudFront WAFs"),
                        help_text=Help(
                            "Include WAFs in front of CloudFront resources in the monitoring."
                        ),
                        value=None,
                    ),
                ),
            },
        ),
        **edition_specific_regional_services(),
    }


def _fromspec_aws_api_access() -> dict[str, DictElement]:
    return {
        "access": DictElement(
            parameter_form=Dictionary(
                title=Title("Access to AWS API"),
                elements={
                    "global_service_region": DictElement(
                        parameter_form=SingleChoice(
                            title=Title("Use custom region for global AWS services"),
                            elements=[
                                SingleChoiceElement(
                                    title=Title("default (all normal AWS regions)"),
                                    name="default",
                                ),
                                *(
                                    SingleChoiceElement(
                                        title=Title(  # pylint: disable=localization-of-non-literal-string
                                            region
                                        ),
                                        name=region.replace("-", "_"),
                                    )
                                    for region in (
                                        "us-gov-east-1",
                                        "us-gov-west-1",
                                        "cn-north-1",
                                        "cn-northwest-1",
                                    )
                                ),
                            ],
                            prefill=DefaultValue("default"),
                        )
                    ),
                    "role_arn_id": DictElement(
                        parameter_form=Dictionary(
                            title=Title("Use STS AssumeRole to assume a different IAM role"),
                            elements={
                                "role_arn": DictElement(
                                    parameter_form=String(
                                        title=Title("The ARN of the IAM role to assume"),
                                        field_size=FieldSize.MEDIUM,
                                        help_text=Help(
                                            "The Amazon Resource Name (ARN) of the role to assume."
                                        ),
                                    ),
                                    required=True,
                                ),
                                "external_id": DictElement(
                                    parameter_form=String(
                                        title=Title("External ID (optional)"),
                                        field_size=FieldSize.MEDIUM,
                                        help_text=Help(
                                            "A unique identifier that might be required when you assume a role in another "
                                            "account. If the administrator of the account to which the role belongs provided "
                                            "you with an external ID, then provide that value in the External ID parameter. "
                                        ),
                                    ),
                                ),
                            },
                        )
                    ),
                },
            ),
            required=True,
        ),
    }


def _formspec_aws_piggyback_naming_convention() -> dict[str, DictElement]:
    return {
        "piggyback_naming_convention": DictElement(
            parameter_form=SingleChoice(
                title=Title("Piggyback names"),
                elements=[
                    SingleChoiceElement(
                        title=Title("IP - Region - Instance ID"),
                        name="ip_region_instance",
                    ),
                    SingleChoiceElement(
                        title=Title("Private IP DNS name"), name="private_dns_name"
                    ),
                ],
                help_text=Help(
                    "Each EC2 instance creates a piggyback host.<br><b>Note:</b> "
                    "Not every hostname is pingable and changing the piggyback name "
                    "will reset the piggyback host.<br><br><b>IP - Region - Instance "
                    'ID:</b><br>The name consists of "{Private IPv4 '
                    'address}-{Region}-{Instance ID}". This uniquely identifies the '
                    "EC2 instance. It is not possible to ping this host name."
                ),
                prefill=DefaultValue("ip_region_instance"),
            ),
            required=True,
        ),
    }


def _migrate_access_vs_to_fs(values: object) -> None:
    if not isinstance(values, dict):
        raise TypeError(values)
    if "global_service_region" in values:
        values["global_service_region"] = values["global_service_region"].replace("-", "_")
    if "role_arn_id" in values:
        if isinstance(values["role_arn_id"], tuple):
            iam_value, external_id_value = values.pop("role_arn_id")
            values["role_arn_id"] = {"role_arn": iam_value, "external_id": external_id_value}


def _migrate_global_services_vs_to_fs(values: object) -> None:
    if not isinstance(values, dict):
        raise TypeError(values)
    values["ce"] = ("all", {}) if "ce" in values else ("none", None)
    migrate_edition_specific_global_services_vs_to_fs(values)


def _migrate_regional_services_vs_to_fs(values: object) -> None:
    if not isinstance(values, dict):
        raise TypeError(values)
    if "lambda" in values:
        values["aws_lambda"] = values.pop("lambda")

    migrate_regional_service(values, "ec2")
    migrate_regional_service(values, "ebs")
    migrate_regional_service(values, "s3")
    migrate_regional_service(values, "glacier")
    migrate_regional_service(values, "elb")
    migrate_regional_service(values, "elbv2")
    migrate_regional_service(values, "rds")
    migrate_regional_service(values, "cloudwatch_alarms", selection_vs_str="alarms")
    migrate_regional_service(values, "dynamodb")
    migrate_regional_service(values, "wafv2")
    migrate_edition_specific_regional_services_vs_to_fs(values)


def _convert_regions(values: object) -> list[str]:
    if not isinstance(values, list):
        raise TypeError(values)
    return [region.replace("-", "_") for region in values]


def _pre_24_to_formspec_migration(values: dict) -> dict[str, object]:
    """Unable to split this into nested migrations due to CMK-17471."""

    # Proxy migrate regions -> regions_to_monitor to indicate migration has been applied
    if "regions_to_monitor" in values:
        return values

    # This migration was present in the server_side_call of the valuespec rule
    # we migrate it here, this can be removed like everything else in 2.5.0
    if "cloudwatch" in values["services"]:
        values["services"]["cloudwatch_alarms"] = values["services"].pop("cloudwatch")

    _migrate_access_vs_to_fs(values["access"])
    values["regions"] = _convert_regions(values["regions"])
    _migrate_global_services_vs_to_fs(values["global_services"])
    _migrate_regional_services_vs_to_fs(values["services"])
    if "overall_tags" in values:
        values["overall_tags"] = convert_tag_list(values["overall_tags"])

    values["regions_to_monitor"] = values.pop("regions")
    return values


def _migrate(values: object) -> dict[str, object]:
    if not isinstance(values, dict):
        raise TypeError(values)
    _pre_24_to_formspec_migration(values)
    handle_edition_switch(values)
    return values


def _formspec_aws():
    return Dictionary(
        title=Title("Amazon Web Services (AWS)"),
        migrate=_migrate,  # Unable to split this due to CMK-17471
        elements={
            "access_key_id": DictElement(
                parameter_form=String(
                    title=Title("The access key ID for your AWS account"),
                    field_size=FieldSize.MEDIUM,
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "secret_access_key": DictElement(
                parameter_form=Password(
                    title=Title("The secret access key for your AWS account"),
                    migrate=migrate_to_password,
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "proxy_details": DictElement(
                parameter_form=Dictionary(
                    title=Title("Proxy server details"),
                    elements={
                        "proxy_host": DictElement(
                            parameter_form=String(title=Title("Proxy host")),
                            required=True,
                        ),
                        "proxy_port": DictElement(
                            parameter_form=Integer(
                                title=Title("Port"),
                                custom_validate=[
                                    validators.NumberInRange(
                                        0, 65535, Message("Port must be between 0 and 65535")
                                    )
                                ],
                            )
                        ),
                        "proxy_user": DictElement(
                            parameter_form=String(
                                title=Title("Username"), field_size=FieldSize.MEDIUM
                            ),
                        ),
                        "proxy_password": DictElement(
                            parameter_form=Password(
                                title=Title("Password"), migrate=migrate_to_password
                            ),
                        ),
                    },
                ),
            ),
            **_fromspec_aws_api_access(),
            "global_services": DictElement(
                parameter_form=Dictionary(
                    title=Title("Global services to monitor"),
                    elements=_global_services(),
                ),
                required=True,
            ),
            "regions_to_monitor": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Regions to monitor"),
                    elements=[
                        MultipleChoiceElement(
                            name=name.replace("-", "_"),
                            title=Title(  # pylint: disable=localization-of-non-literal-string
                                title
                            ),
                        )
                        for name, title in aws_region_to_monitor()
                    ],
                ),
                required=True,
            ),
            "services": DictElement(
                parameter_form=Dictionary(
                    title=Title("Services per region to monitor"),
                    elements=_regional_services(),
                ),
                required=True,
            ),
            **_formspec_aws_piggyback_naming_convention(),
            "overall_tags": DictElement(
                parameter_form=formspec_aws_tags(
                    Title("Restrict monitoring services by one of these AWS tags")
                ),
            ),
        },
    )


rule_spec_aws = SpecialAgent(
    name="aws",
    title=Title("Amazon Web Services (AWS)"),
    topic=Topic.CLOUD,
    parameter_form=_formspec_aws,
)
