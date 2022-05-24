#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils import aws_constants

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import (
    RulespecGroupVMCloudContainer,
    validate_aws_tags,
)
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    FixedValue,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    TextInput,
    Transform,
    Tuple,
)


def _vs_aws_tags(title):
    return ListOf(
        valuespec=Tuple(
            help=_(
                "How to configure AWS tags please see "
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
                "<i>Gather all service instances and restrict by overall tags</i> means that "
                "if overall tags are stated above then all service instances are filtered "
                "by these tags. Otherwise all instances are gathered.<br>"
                "With <i>Use explicit service tags and overwrite overall tags</i> you can "
                "specify explicit tags for these services. The overall tags are ignored for "
                "these services.<br>"
                "<i>Use explicit service names and ignore overall tags</i>: With this selection "
                "you can state explicit names. The overall tags are ignored for these service."
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
                "If limits are enabled all instances are fetched regardless of "
                "possibly configured restriction to names or tags"
            ),
            title=_("Service limits"),
            totext=_("Monitor service limits"),
        ),
    )


def _transform_aws(d):
    services = d["services"]
    if "cloudwatch" in services:
        services["cloudwatch_alarms"] = services["cloudwatch"]
        del services["cloudwatch"]
    if "assume_role" not in d:
        d["assume_role"] = {}
    return d


def _valuespec_special_agents_aws():
    return Transform(
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
                    IndividualOrStoredPassword(
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
                            ("proxy_password", IndividualOrStoredPassword(title=_("Password"))),
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
                    Dictionary(
                        title=_("Global services to monitor"),
                        elements=[
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
                                FixedValue(
                                    value=None, totext=_("Monitor Route53"), title=_("Route53")
                                ),
                            ),
                        ],
                    ),
                ),
                (
                    "regions",
                    ListChoice(
                        title=_("Regions to use"),
                        choices=sorted(aws_constants.AWSRegions, key=lambda x: x[1]),
                    ),
                ),
                (
                    "services",
                    Dictionary(
                        title=_("Services per region to monitor"),
                        elements=[
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
                                                totext=_("Monitor request metrics"),
                                                title=_("Request metrics"),
                                                help=_(
                                                    "In order to monitor S3 request metrics you have to "
                                                    "enable request metric monitoring in the AWS/S3 console. "
                                                    "This is a paid feature"
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
                                                    "Include WAFs in front of CloudFront resources in the "
                                                    "monitoring"
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
                        ],
                        default_keys=[
                            "ec2",
                            "ebs",
                            "s3",
                            "glacier",
                            "elb",
                            "elbv2",
                            "rds",
                            "cloudwatch_alarms",
                            "dynamodb",
                            "wafv2",
                            "lambda",
                            "sns",
                        ],
                    ),
                ),
                (
                    "overall_tags",
                    _vs_aws_tags(_("Restrict monitoring services by one of these AWS tags")),
                ),
            ],
            optional_keys=["overall_tags", "proxy_details"],
        ),
        forth=_transform_aws,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:aws",
        title=lambda: _("Amazon Web Services (AWS)"),
        valuespec=_valuespec_special_agents_aws,
    )
)
