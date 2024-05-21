#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any, Literal

from cmk.plugins.aws.lib import aws_region_to_monitor
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    FormSpec,
    Integer,
    List,
    migrate_to_password,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _all_global_services() -> dict[str, DictElement]:
    return {
        "ce": _service_dict_element(
            Title("Costs and usage (CE)"),
            {},
            default_enabled=False,
            filterable_by_name=False,
            filterable_by_tags=False,
        ),
        "route53": _service_dict_element(
            Title("Route53"),
            {},
            default_enabled=False,
            filterable_by_name=False,
            filterable_by_tags=False,
        ),
        "cloudfront": _service_dict_element(
            Title("CloudFront"),
            {
                "host_assignment": DictElement(
                    parameter_form=SingleChoice(
                        title=Title("Define host assignment"),
                        help_text=Help(
                            "Define the host to assign the discovered CloudFront services."
                            " You can assign them to the AWS host as any other AWS service or"
                            " to a piggyback host that will be named as the 'Origin Domain'"
                            " specified in the CloudFront distribution - in case you select the"
                            " second option, you will have to create the piggyback host(s)"
                        ),
                        elements=[
                            SingleChoiceElement(
                                title=Title("Assign services to AWS host"),
                                name="aws_host",
                            ),
                            SingleChoiceElement(
                                title=Title(
                                    "Assign services to piggyback host(s) named as the 'Origin Domain' configured in AWS"
                                ),
                                name="domain_host",
                            ),
                        ],
                        prefill=DefaultValue("aws_host"),
                    ),
                    required=True,
                ),
            },
            default_enabled=False,
        ),
    }


def _service_dict_element(
    title: Title,
    extra_elements: dict[str, DictElement],
    default_enabled: bool = True,
    filterable_by_tags: bool = True,
    filterable_by_name: bool = True,
) -> DictElement:
    elements: list[CascadingSingleChoiceElement] = [
        CascadingSingleChoiceElement(
            title=Title("Do not monitor service"),
            name="none",
            parameter_form=FixedValue(value=None),
        ),
        CascadingSingleChoiceElement(
            name="all",
            title=Title("Monitor all instances"),
            parameter_form=Dictionary(
                elements={
                    **extra_elements,
                }
            ),
        ),
    ]
    if filterable_by_tags:
        elements.append(
            CascadingSingleChoiceElement(
                name="tags",
                title=Title(
                    "Monitor instances with explicit AWS service tags ignoring overall tag filters"
                ),
                parameter_form=Dictionary(
                    elements={
                        "tags": DictElement(
                            parameter_form=_formspec_aws_tags(),
                            required=True,
                        ),
                        **extra_elements,
                    },
                ),
            )
        )
    if filterable_by_name:
        elements.append(
            CascadingSingleChoiceElement(
                name="names",
                title=Title(
                    "Monitor instances with explicit service names ignoring overall tag filters"
                ),
                parameter_form=Dictionary(
                    elements={
                        "names": DictElement(
                            parameter_form=List(
                                element_template=String(label=Label("Service name")),
                                add_element_label=Label("Add new name"),
                                remove_element_label=Label("Remove name"),
                                no_element_label=Label("No names defined"),
                                editable_order=False,
                            ),
                            required=True,
                        ),
                        **extra_elements,
                    },
                ),
            )
        )

    return DictElement(
        parameter_form=CascadingSingleChoice(
            help_text=Help(
                "<b>Monitor all instances:</b> "
                "<br>If overall tags are specified below, then all "
                "service instances will be filtered by those tags. Otherwise, "
                "all instances will be collected.<br><br><b>Monitor instances "
                "with explicit AWS service tags ignoring overall tag "
                "filters:</b><br>Specify explicit tags for these services. The "
                "overall tags will be ignored for these services.<br><br><b>Monitor "
                "instances with explicit service names ignoring overall tag "
                "filters:</b><br>Use this option to specify explicit names. "
                "The overall tags will be ignored for these services."
            ),
            title=title,
            elements=elements,
            prefill=DefaultValue("all" if default_enabled else "none"),
        ),
        required=True,
    )


def _all_regional_services() -> dict[str, DictElement]:
    return {
        "ec2": _service_dict_element(
            Title("Elastic Compute Cloud (EC2)"), extra_elements=_formspec_aws_limits()
        ),
        "ebs": _service_dict_element(
            Title("Elastic Block Storage (EBS)"), extra_elements=_formspec_aws_limits()
        ),
        "s3": _service_dict_element(
            Title("Simple Storage Service (S3)"),
            {
                **_formspec_aws_limits(),
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
        "glacier": _service_dict_element(
            Title("Amazon S3 Glacier (Glacier)"), extra_elements=_formspec_aws_limits()
        ),
        "elb": _service_dict_element(
            Title("Classic Load Balancing (ELB)"), extra_elements=_formspec_aws_limits()
        ),
        "elbv2": _service_dict_element(
            Title("Application and Network Load Balancing (ELBv2)"),
            extra_elements=_formspec_aws_limits(),
        ),
        "rds": _service_dict_element(
            Title("Relational Database Service (RDS)"), extra_elements=_formspec_aws_limits()
        ),
        "cloudwatch_alarms": _service_dict_element(
            Title("CloudWatch Alarms"), _formspec_aws_limits(), filterable_by_tags=False
        ),
        "dynamodb": _service_dict_element(Title("DynamoDB"), extra_elements=_formspec_aws_limits()),
        "wafv2": _service_dict_element(
            Title("Web Application Firewall (WAFV2)"),
            extra_elements={
                **_formspec_aws_limits(),
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
        "aws_lambda": _service_dict_element(Title("Lambda"), extra_elements=_formspec_aws_limits()),
        "sns": _service_dict_element(
            Title("Simple Notification Service (SNS)"), extra_elements=_formspec_aws_limits()
        ),
        "ecs": _service_dict_element(
            Title("Elastic Container Service (ECS)"), extra_elements=_formspec_aws_limits()
        ),
        "elasticache": _service_dict_element(
            Title("ElastiCache"), extra_elements=_formspec_aws_limits()
        ),
    }


def _formspec_aws_limits() -> dict[str, DictElement]:
    return {
        "limits": DictElement(
            required=True,
            parameter_form=SingleChoice(
                title=Title("Service limits"),
                elements=[
                    SingleChoiceElement(
                        title=Title("Monitor limits"),
                        name="limits",
                    ),
                    SingleChoiceElement(
                        title=Title("Do not monitor limits"),
                        name="no_limits",
                    ),
                ],
                prefill=DefaultValue("limits"),
                help_text=Help(
                    "If limits are monitored, all instances will be fetched "
                    "regardless of any name or tag restrictions that may have been "
                    "configured."
                ),
            ),
        )
    }


def _validate_aws_tags(values: Sequence[Any]) -> object:
    used_keys = []
    for tag_dict in values:
        tag_key = tag_dict["key"]
        tag_values = tag_dict["values"]
        if tag_key not in used_keys:
            used_keys.append(tag_key)
        else:
            raise ValidationError(
                Message("Each tag key must be unique and cannot be used multiple times.")
            )
        if tag_key.startswith("aws:"):
            raise ValidationError(Message("Do not use 'aws:' prefix for the key."))
        if len(tag_key) > 128:
            raise ValidationError(Message("The maximum key length is 128 characters."))
        if len(values) > 50:
            raise ValidationError(Message("The maximum number of tags per resource is 50."))
        for tag_value in tag_values:
            if len(tag_value) > 256:
                raise ValidationError(Message("The maximum value length is 256 characters."))
            if tag_value.startswith("aws:"):
                raise ValidationError(Message("Do not use 'aws:' prefix for the value."))
    return values


def _formspec_aws_tags(title: Title | None = None) -> FormSpec:
    return List(
        help_text=Help(
            "For information on AWS tag configuration, visit "
            "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html"
        ),
        title=title,
        element_template=Dictionary(
            elements={
                "key": DictElement(
                    parameter_form=String(
                        title=Title("Key"),
                    ),
                    required=True,
                ),
                "values": DictElement(
                    parameter_form=List(
                        element_template=String(label=Label("Value")),
                        add_element_label=Label("Add new value"),
                        remove_element_label=Label("Remove value"),
                        no_element_label=Label("No values defined"),
                        editable_order=False,
                    ),
                    required=True,
                ),
            },
        ),
        add_element_label=Label("Add new tag"),
        remove_element_label=Label("Remove tag"),
        no_element_label=Label("No tags defined"),
        editable_order=False,
        custom_validate=[_validate_aws_tags],
    )


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
    assert isinstance(values, dict)
    if "global_service_region" in values:
        values["global_service_region"] = values["global_service_region"].replace("-", "_")
    if "role_arn_id" in values:
        if isinstance(values["role_arn_id"], tuple):
            iam_value, external_id_value = values.pop("role_arn_id")
            values["role_arn_id"] = {"role_arn": iam_value, "external_id": external_id_value}
        assert not isinstance(values["role_arn_id"], tuple)


def _convert_tag_list(tags: list[tuple[str, list[str] | str]]) -> list[dict[str, list[str] | str]]:
    return [
        {"key": key, "values": values if isinstance(values, list) else [values]}
        for key, values in tags
    ]


def _convert_selection(
    selection: Any,
) -> tuple[Literal["all", "tags", "names"], dict[str, object]]:
    if selection == "all":
        return "all", {}
    selection_type, selection_values = selection
    if selection_type == "tags":
        assert isinstance(selection_values, list)
        return selection_type, {"tags": _convert_tag_list(selection_values)}
    if selection_type == "names":
        return selection_type, {"names": selection_values}

    raise ValueError(f"Unknown selection type: {selection_type}")


def _migrate_global_services_vs_to_fs(values: object) -> None:
    assert isinstance(values, dict)
    values["ce"] = ("all", {}) if "ce" in values else ("none", None)
    values["route53"] = ("all", {}) if "route53" in values else ("none", None)
    _migrate_global_service(values, "cloudfront")


def _migrate_global_service(values: dict, service: str) -> None:
    if service not in values:
        values[service] = ("none", None)

    if isinstance(values[service], dict):
        selection, selection_vars = _convert_selection(values[service].pop("selection"))
        values[service] = (
            selection,
            {**selection_vars, **values[service]},
        )


def _migrate_regional_service(
    values: dict, service: str, selection_vs_str: str = "selection"
) -> None:
    if service not in values:
        values[service] = ("none", None)

    if isinstance(values[service], dict):
        if "limits" in values[service]:
            values[service]["limits"] = "limits"
        else:
            values[service]["limits"] = "no_limits"

        selection, selection_vars = _convert_selection(values[service].pop(selection_vs_str))
        values[service] = (
            selection,
            {**selection_vars, **values[service]},
        )


def _migrate_regional_services_vs_to_fs(values: object) -> None:
    assert isinstance(values, dict)
    if "lambda" in values:
        values["aws_lambda"] = values.pop("lambda")

    _migrate_regional_service(values, "ec2")
    _migrate_regional_service(values, "ebs")
    _migrate_regional_service(values, "s3")
    _migrate_regional_service(values, "glacier")
    _migrate_regional_service(values, "elb")
    _migrate_regional_service(values, "elbv2")
    _migrate_regional_service(values, "rds")
    _migrate_regional_service(values, "cloudwatch_alarms", selection_vs_str="alarms")
    _migrate_regional_service(values, "dynamodb")
    _migrate_regional_service(values, "wafv2")
    _migrate_regional_service(values, "aws_lambda")
    _migrate_regional_service(values, "sns")
    _migrate_regional_service(values, "ecs")
    _migrate_regional_service(values, "elasticache")


def _convert_regions(values: object) -> list[str]:
    assert isinstance(values, list)
    return [region.replace("-", "_") for region in values]


def _pre_24_to_formspec_migration(values: object) -> dict[str, object]:
    """Unable to split this into nested migrations due to CMK-17471."""
    assert isinstance(values, dict)

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
        values["overall_tags"] = _convert_tag_list(values["overall_tags"])

    values["regions_to_monitor"] = values.pop("regions")
    return values


def _formspec_aws():
    return Dictionary(
        title=Title("Amazon Web Services (AWS)"),
        migrate=_pre_24_to_formspec_migration,  # Unable to split this due to CMK-17471
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
                    elements=_all_global_services(),
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
                    elements=_all_regional_services(),
                ),
                required=True,
            ),
            **_formspec_aws_piggyback_naming_convention(),
            "overall_tags": DictElement(
                parameter_form=_formspec_aws_tags(
                    Title("Restrict monitoring services by one of these AWS tags")
                ),
            ),
        },
    )


rule_spec_aws = SpecialAgent(
    name="aws_dev_internal",
    title=Title("(dev internal, unreleased) Amazon Web Services (AWS)"),
    topic=Topic.CLOUD,
    parameter_form=_formspec_aws,
)
