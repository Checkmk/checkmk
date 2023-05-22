#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container
from typing import Iterable, TypeVar

from cmk.utils.version import is_cloud_edition

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import (
    aws_region_to_monitor,
    RulespecGroupVMCloudContainer,
    validate_aws_tags,
)
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    MigrateToIndividualOrStoredPassword,
    rulespec_registry,
)
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DictionaryEntry,
    FixedValue,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    Migrate,
    MigrateNotUpdated,
    TextInput,
    Tuple,
    ValueSpec,
)

ServicesValueSpec = list[tuple[str, ValueSpec]]


def _vs_aws_tags(title):
    return ListOf(
        valuespec=Tuple(
            help=_(
                "For information on AWS tag configuration, visit "
                "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html"
            ),
            orientation="horizontal",
            elements=[
                TextInput(title=_("Key")),
                ListOfStrings(title=_("Values"), orientation="horizontal"),
            ],
        ),
        add_label=_("Add new tag"),
        movable=False,
        title=title,
        validate=validate_aws_tags,
    )


def _vs_element_aws_service_selection():
    return (
        "selection",
        CascadingDropdown(
            title=_("Selection of service instances"),
            help=_(
                "<b>Gather all service instances and restrict by overall "
                "tags:</b><br>If overall tags are specified above, then all "
                "service instances will be filtered by those tags. Otherwise, "
                "all instances will be collected.<br><br><b>Explicit service "
                "tags and overwrite overall tags:</b><br>Specify explicit "
                "tags for these services. The overall tags will be ignored for "
                "these services.<br><br><b>Explicit service names and ignore "
                "overall tags:</b><br>Use this option to specify explicit names. "
                "The overall tags will be ignored for these services."
            ),
            choices=[
                ("all", _("Gather all service instances and restrict by overall AWS tags")),
                (
                    "tags",
                    _("Use explicit AWS service tags and overrule overall AWS tags"),
                    _vs_aws_tags(_("AWS Tags")),
                ),
                (
                    "names",
                    _("Use explicit service names and ignore overall AWS tags"),
                    ListOfStrings(),
                ),
            ],
        ),
    )


def _vs_element_aws_limits():
    return (
        "limits",
        FixedValue(
            value=True,
            help=_(
                "If limits are enabled, all instances will be fetched "
                "regardless of any name or tag restrictions that may have been "
                "configured."
            ),
            title=_("Service limits"),
            totext=_("Monitor service limits"),
        ),
    )


def _vs_element_aws_piggyback_naming_convention() -> DictionaryEntry:
    return (
        "piggyback_naming_convention",
        CascadingDropdown(
            title=_("Piggyback names"),
            choices=[
                (
                    "ip_region_instance",
                    _("IP - region - instance ID"),
                ),
                (
                    "private_dns_name",
                    _("Private IP DNS name"),
                ),
            ],
            help=_(
                "Each EC2 instance creates a piggyback host.<br><b>Note:</b> "
                "Not every hostname is pingable and changing the piggyback name "
                "will reset the piggyback host.<br><br><b>IP - Region - Instance "
                'ID:</b><br>The name consists of "{Private IPv4 '
                'address}-{Region}-{Instance ID}". This uniquely identifies the '
                "EC2 instance. It is not possible to ping this host name."
            ),
        ),
    )


T = TypeVar("T")


class AWSSpecialAgentValuespecBuilder:
    # Global services that should be present just in the CMK cloud edition
    CCE_ONLY_GLOBAL_SERVICES = {"cloudfront", "route53"}
    # Regional services that should be present just in the CMK cloud edition
    CCE_ONLY_REGIONAL_SERVICES = {"sns", "lambda", "ecs", "elasticache"}

    def __init__(self, cloud_edition: bool):
        self.is_cloud_edition = cloud_edition

    def get_global_services(self) -> ServicesValueSpec:
        return self.filter_for_edition(
            self._get_all_global_services(), self.CCE_ONLY_GLOBAL_SERVICES
        )

    def get_regional_services(self) -> ServicesValueSpec:
        return self.filter_for_edition(
            self._get_all_regional_services(), self.CCE_ONLY_REGIONAL_SERVICES
        )

    def filter_for_edition(
        self, all_services: Iterable[tuple[str, T]], cce_only_services: Container[str]
    ) -> list[tuple[str, T]]:
        if self.is_cloud_edition:
            return list(all_services)
        return [s for s in all_services if s[0] not in cce_only_services]

    def _get_all_global_services(self) -> ServicesValueSpec:
        return [
            (
                "ce",
                FixedValue(
                    value=None,
                    totext=_("Monitor costs and usage"),
                    title=_("Costs and usage (CE)"),
                ),
            ),
            (
                "route53",
                FixedValue(value=None, totext=_("Monitor Route53"), title=_("Route53")),
            ),
            (
                "cloudfront",
                Dictionary(
                    title=_("CloudFront"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        (
                            "host_assignment",
                            CascadingDropdown(
                                title=_("Define Host Assignment"),
                                help=_(
                                    "Define the host to assign the discovered CloudFront services."
                                    " You can assign them to the AWS host as any other AWS service or"
                                    " to a piggyback host that will be named as the 'Origin Domain'"
                                    " specified in the CloudFront distribution - in case you select the"
                                    " second option, you will have to create the piggyback host(s)"
                                ),
                                choices=[
                                    (
                                        "aws_host",
                                        _("Assign services to AWS host"),
                                    ),
                                    (
                                        "domain_host",
                                        _(
                                            "Assign services to piggyback host(s) named as the"
                                            " 'Origin Domain' configured in AWS"
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    ],
                    default_keys=[],
                    optional_keys=[],
                ),
            ),
        ]

    def _get_all_regional_services(self) -> ServicesValueSpec:
        return [
            (
                "ec2",
                Dictionary(
                    title=_("Elastic Compute Cloud (EC2)"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
            (
                "ebs",
                Dictionary(
                    title=_("Elastic Block Storage (EBS)"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
            (
                "s3",
                Dictionary(
                    title=_("Simple Storage Service (S3)"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                        (
                            "requests",
                            FixedValue(
                                value=None,
                                totext=_(
                                    "Monitor request metrics using the filter <tt>EntireBucket</tt>"
                                ),
                                title=_("Request metrics"),
                                help=_(
                                    "In order to monitor S3 request metrics, you have to enable "
                                    "request metrics in the AWS/S3 console, see the "
                                    "<a href='https://docs.aws.amazon.com/AmazonS3/latest/userguide/metrics-configurations.html'>AWS/S3 documentation</a>. "
                                    "This is a paid feature. Note that the filter name has to be "
                                    "set to <tt>EntireBucket</tt>, as is recommended in the "
                                    "<a href='https://docs.aws.amazon.com/AmazonS3/latest/userguide/configure-request-metrics-bucket.html'>documentation for a filter that applies to all objects</a>. "
                                    "The special agent will use this filter name to query S3 request "
                                    "metrics from the AWS API."
                                ),
                            ),
                        ),
                    ],
                    optional_keys=["limits", "requests"],
                    default_keys=["limits"],
                ),
            ),
            (
                "glacier",
                Dictionary(
                    title=_("Amazon S3 Glacier (Glacier)"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
            (
                "elb",
                Dictionary(
                    title=_("Classic Load Balancing (ELB)"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
            (
                "elbv2",
                Dictionary(
                    title=_("Application and Network Load Balancing (ELBv2)"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
            (
                "rds",
                Dictionary(
                    title=_("Relational Database Service (RDS)"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
            (
                "cloudwatch_alarms",
                Dictionary(
                    title=_("CloudWatch Alarms"),
                    elements=[
                        (
                            "alarms",
                            CascadingDropdown(
                                title=_("Selection of alarms"),
                                choices=[
                                    ("all", _("Gather all")),
                                    (
                                        "names",
                                        _("Use explicit names"),
                                        ListOfStrings(),
                                    ),
                                ],
                            ),
                        ),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["alarms", "limits"],
                    default_keys=["alarms", "limits"],
                ),
            ),
            (
                "dynamodb",
                Dictionary(
                    title=_("DynamoDB"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
            (
                "wafv2",
                Dictionary(
                    title=_("Web Application Firewall (WAFV2)"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                        (
                            "cloudfront",
                            FixedValue(
                                value=None,
                                totext=_("Monitor CloudFront WAFs"),
                                title=_("CloudFront WAFs"),
                                help=_(
                                    "Include WAFs in front of CloudFront "
                                    "resources in the monitoring."
                                ),
                            ),
                        ),
                    ],
                    optional_keys=["limits", "cloudfront"],
                    default_keys=["limits", "cloudfront"],
                ),
            ),
            (
                "lambda",
                Dictionary(
                    title=_("Lambda"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
            (
                "sns",
                Dictionary(
                    title=_("Simple Notification Service (SNS)"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
            (
                "ecs",
                Dictionary(
                    title=_("Elastic Container Service (ECS)"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
            (
                "elasticache",
                Dictionary(
                    title=_("ElastiCache"),
                    elements=[
                        _vs_element_aws_service_selection(),
                        _vs_element_aws_limits(),
                    ],
                    optional_keys=["limits"],
                    default_keys=["limits"],
                ),
            ),
        ]


def _valuespec_special_agents_aws() -> Migrate:
    valuespec_builder = AWSSpecialAgentValuespecBuilder(is_cloud_edition())
    global_services = valuespec_builder.get_global_services()
    regional_services = valuespec_builder.get_regional_services()
    regional_services_default_keys = [service[0] for service in regional_services]

    return Migrate(
        valuespec=Dictionary(
            title=_("Amazon Web Services (AWS)"),
            elements=[
                (
                    "access_key_id",
                    TextInput(
                        title=_("The access key ID for your AWS account"),
                        allow_empty=False,
                        size=50,
                    ),
                ),
                (
                    "secret_access_key",
                    MigrateToIndividualOrStoredPassword(
                        title=_("The secret access key for your AWS account"),
                        allow_empty=False,
                    ),
                ),
                (
                    "proxy_details",
                    Dictionary(
                        title=_("Proxy server details"),
                        elements=[
                            ("proxy_host", TextInput(title=_("Proxy host"), allow_empty=False)),
                            ("proxy_port", Integer(title=_("Port"))),
                            (
                                "proxy_user",
                                TextInput(
                                    title=_("Username"),
                                    size=32,
                                ),
                            ),
                            (
                                "proxy_password",
                                MigrateToIndividualOrStoredPassword(title=_("Password")),
                            ),
                        ],
                        optional_keys=["proxy_port", "proxy_user", "proxy_password"],
                    ),
                ),
                (
                    "assume_role",
                    Dictionary(
                        title=_("Assume a different IAM role"),
                        elements=[
                            (
                                "role_arn_id",
                                Tuple(
                                    title=_("Use STS AssumeRole to assume a different IAM role"),
                                    elements=[
                                        TextInput(
                                            title=_("The ARN of the IAM role to assume"),
                                            size=50,
                                            help=_(
                                                "The Amazon Resource Name (ARN) of the role to assume."
                                            ),
                                        ),
                                        TextInput(
                                            title=_("External ID (optional)"),
                                            size=50,
                                            help=_(
                                                "A unique identifier that might be required when you assume a role in another "
                                                "account. If the administrator of the account to which the role belongs provided "
                                                "you with an external ID, then provide that value in the External ID parameter. "
                                            ),
                                        ),
                                    ],
                                ),
                            )
                        ],
                    ),
                ),
                (
                    "global_services",
                    MigrateNotUpdated(
                        valuespec=Dictionary(
                            title=_("Global services to monitor"),
                            elements=global_services,
                        ),
                        migrate=lambda p: dict(
                            valuespec_builder.filter_for_edition(
                                p.items(), valuespec_builder.CCE_ONLY_GLOBAL_SERVICES
                            )
                        ),
                    ),
                ),
                (
                    "regions",
                    ListChoice(
                        title=_("Regions to monitor"),
                        choices=aws_region_to_monitor(),
                    ),
                ),
                (
                    "services",
                    MigrateNotUpdated(
                        valuespec=Dictionary(
                            title=_("Services per region to monitor"),
                            elements=regional_services,
                            default_keys=regional_services_default_keys,
                        ),
                        migrate=lambda p: dict(
                            valuespec_builder.filter_for_edition(
                                p.items(), valuespec_builder.CCE_ONLY_REGIONAL_SERVICES
                            )
                        ),
                    ),
                ),
                _vs_element_aws_piggyback_naming_convention(),
                (
                    "overall_tags",
                    _vs_aws_tags(_("Restrict monitoring services by one of these AWS tags")),
                ),
            ],
            optional_keys=["overall_tags", "proxy_details"],
        ),
        migrate=lambda p: {"piggyback_naming_convention": "ip_region_instance"} | p,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:aws",
        title=lambda: _("Amazon Web Services (AWS)"),
        valuespec=_valuespec_special_agents_aws,
        doc_references={DocReference.AWS: _("Monitoring Amazon Web Services (AWS)")},
    )
)
