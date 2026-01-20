#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="unreachable"

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

from collections.abc import Container, Iterable, Sequence
from typing import Literal, TypeVar

import cmk.utils.paths
from cmk.ccc.version import Edition, edition
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    FixedValue,
    ListChoice,
    ListOf,
    ListOfStrings,
    Migrate,
    MigrateNotUpdated,
    NetworkPort,
    TextInput,
    Transform,
    Tuple,
    ValueSpec,
)
from cmk.gui.valuespec.definitions import RegExp
from cmk.gui.wato import IndividualOrStoredPassword, RulespecGroupVMCloudContainer
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry
from cmk.plugins.aws.lib import aws_region_to_monitor  # astrein: disable=cmk-module-layer-violation
from cmk.rulesets.v1.form_specs import migrate_to_password
from cmk.utils.rulesets.definition import RuleGroup

ServicesValueSpec = list[tuple[str, ValueSpec]]


def _unmigrate_password(
    model: tuple[
        Literal["cmk_postprocessed"],
        Literal["explicit_password", "stored_password"],
        tuple[str, str],
    ],
) -> object:
    match model:
        case "password", password:
            return "password", password
        case "store", password_store_id:
            return "store", password_store_id
        # already migrated passwords
        case "cmk_postprocessed", "explicit_password", (str(_password_id), str(password)):
            return "password", password
        case "cmk_postprocessed", "stored_password", (str(password_store_id), str(_password)):
            return "store", password_store_id

    raise TypeError(f"Could not migrate {model!r} to Password.")


def _vs_v1_ssc_password(title: str, allow_empty: bool) -> ValueSpec:
    """
    This makes sure we can use the v1 server-side call API within a valuespec.
    The reason this is necessary is that it has been decided that this rule needs considerable
    changes to be migrated to FormSpecs. This is a temporary solution to make sure the rule
    still transmits passwords in a secure way to the agent.
    """
    return Migrate(
        Transform(
            valuespec=IndividualOrStoredPassword(title=title, allow_empty=allow_empty),
            back=migrate_to_password,
            forth=_unmigrate_password,
        ),
        migrate=lambda v: ("password", v) if not isinstance(v, tuple) else v,
    )


def _validate_aws_tags(value: Sequence[tuple[str, Sequence[str]]], varprefix: str) -> None:
    used_keys = []
    # KEY:
    # ve_p_services_p_ec2_p_choice_1_IDX_0
    # VALUES:
    # ve_p_services_p_ec2_p_choice_1_IDX_1_IDX
    for idx_tag, (tag_key, tag_values) in enumerate(value):
        tag_field = f"{varprefix}_{idx_tag + 1}_0"
        if tag_key not in used_keys:
            used_keys.append(tag_key)
        else:
            raise MKUserError(
                tag_field, _("Each tag must be unique and cannot be used multiple times")
            )
        if tag_key.startswith("aws:"):
            raise MKUserError(tag_field, _("Do not use 'aws:' prefix for the key."))
        if len(tag_key) > 128:
            raise MKUserError(tag_field, _("The maximum key length is 128 characters."))
        if len(tag_values) > 50:
            raise MKUserError(tag_field, _("The maximum number of tags per resource is 50."))

        for idx_values, v in enumerate(tag_values):
            values_field = f"{varprefix}_{idx_tag + 1}_1_{idx_values + 1}"
            if len(v) > 256:
                raise MKUserError(values_field, _("The maximum value length is 256 characters."))
            if v.startswith("aws:"):
                raise MKUserError(values_field, _("Do not use 'aws:' prefix for the values."))


def _vs_aws_tags(title: str) -> ListOf:
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
        validate=_validate_aws_tags,
    )


def _vs_element_aws_service_selection() -> DictionaryEntry:
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
                (
                    "all",
                    _("Gather all service instances and restrict by overall AWS tags"),
                ),
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


def _vs_element_aws_limits() -> DictionaryEntry:
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
                "Not every host name is pingable and changing the piggyback name "
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

    def __init__(self, cloud_edition: bool) -> None:
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
                                title=_("Define host assignment"),
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


def _migrate(value: object) -> dict[str, object]:
    """
    migrate to new auth config with explicit auth types
    migrate key "services" to "regional_services" and add default for "import_tags"
    """

    assert isinstance(value, dict)

    if "auth" not in value:
        auth = {}
        if "access_key_id" in value:
            auth["access_key_id"] = value["access_key_id"]
            auth["secret_access_key"] = value["secret_access_key"]

            # values required for migration 2.3->2.4 reuse for 2.5
            del value["access_key_id"]
            del value["secret_access_key"]

        if "access" not in value or "role_arn_id" not in value["access"]:
            value["auth"] = ("access_key", auth)
        else:
            auth["role_arn_id"] = value["access"]["role_arn_id"][0]

            if value["access"]["role_arn_id"][1]:
                auth["external_id"] = value["access"]["role_arn_id"][1]

            # values required for migration 2.3->2.4 reuse for 2.5
            del value["access"]["role_arn_id"]
            value["auth"] = ("access_key_sts", auth)

    # "services" was renamed to "regional_services" as a surrogate migration in 2.4.0 to add the
    # optional parameter "import_tags". By default, "import_tags" is unselected (set to None) so no
    # tags are imported with a new default config, while in earlier configs without this parameter
    # all tags were imported at all times.
    # So to detect old configs we check for the old key "services" to set "import_tags" to import
    # all tags ("all_tags"). Checking for a missing param "import_tags" does not work as that's the
    # parameter's default.
    # Note that if "regional_services" is renamed back to "services" in the future, this needs to
    # be done for both the rule and the quick setup code.
    if "services" in value:
        assert "regional_services" not in value
        value["regional_services"] = value.pop("services")
        value["import_tags"] = ("all_tags", None)

    return value


def _valuespec_special_agents_aws() -> Migrate:
    valuespec_builder = AWSSpecialAgentValuespecBuilder(
        edition(cmk.utils.paths.omd_root) in (Edition.ULTIMATEMT, Edition.ULTIMATE, Edition.CLOUD)
    )
    global_services = valuespec_builder.get_global_services()
    regional_services = valuespec_builder.get_regional_services()
    regional_services_default_keys = [service[0] for service in regional_services]

    return Migrate(
        Dictionary(
            title=_("Amazon Web Services (AWS)"),
            optional_keys=[
                "overall_tags",
                "proxy_details",
                "import_tags",
            ],
            elements=[
                (
                    "auth",
                    CascadingDropdown(
                        title=_("Authentication type"),
                        help=_(
                            "Monitoring via an IAM role is recommended, however it requires the monitoring site to be "
                            "located on an AWS EC2 instance with the according permissions to the accounts to be monitored."
                        ),
                        choices=[
                            (
                                "access_key",
                                _("Access key"),
                                Dictionary(
                                    title=_("Proxy server details"),
                                    optional_keys=False,
                                    elements=[
                                        (
                                            "access_key_id",
                                            TextInput(
                                                title=_("The access key ID for your AWS account"),
                                                allow_empty=True,
                                                size=50,
                                            ),
                                        ),
                                        (
                                            "secret_access_key",
                                            _vs_v1_ssc_password(
                                                title=_(
                                                    "The secret access key for your AWS account"
                                                ),
                                                allow_empty=False,
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                            (
                                "access_key_sts",
                                _("Access key + IAM role"),
                                Dictionary(
                                    title=_("Access key information"),
                                    optional_keys=["external_id"],
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
                                            _vs_v1_ssc_password(
                                                title=_(
                                                    "The secret access key for your AWS account"
                                                ),
                                                allow_empty=False,
                                            ),
                                        ),
                                        (
                                            "role_arn_id",
                                            TextInput(
                                                title=_("The ARN of the IAM role to assume"),
                                                size=50,
                                                allow_empty=False,
                                                help=_(
                                                    "The Amazon Resource Name (ARN) of the role to assume."
                                                ),
                                            ),
                                        ),
                                        (
                                            "external_id",
                                            TextInput(
                                                title=_("External ID"),
                                                size=50,
                                                allow_empty=True,
                                                help=_(
                                                    "A unique identifier that might be required when you assume a role in another "
                                                    "account. If the administrator of the account to which the role belongs provided "
                                                    "you with an external ID, then provide that value in the External ID parameter. "
                                                ),
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                            (
                                "sts",
                                _("IAM role (on EC2 instance only)"),
                                Dictionary(
                                    title=_("Access key information"),
                                    optional_keys=["external_id"],
                                    elements=[
                                        (
                                            "role_arn_id",
                                            TextInput(
                                                title=_("The ARN of the IAM role to assume"),
                                                size=50,
                                                allow_empty=False,
                                                help=_(
                                                    "The Amazon Resource Name (ARN) of the role to assume."
                                                ),
                                            ),
                                        ),
                                        (
                                            "external_id",
                                            TextInput(
                                                title=_("External ID"),
                                                size=50,
                                                allow_empty=True,
                                                help=_(
                                                    "A unique identifier that might be required when you assume a role in another "
                                                    "account. If the administrator of the account to which the role belongs provided "
                                                    "you with an external ID, then provide that value in the External ID parameter. "
                                                ),
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                            (
                                "none",
                                _("None (on EC2 instance only)"),
                            ),
                        ],
                    ),
                ),
                (
                    "proxy_details",
                    Dictionary(
                        title=_("Proxy server details"),
                        elements=[
                            ("proxy_host", TextInput(title=_("Proxy host"), allow_empty=False)),
                            ("proxy_port", NetworkPort(title=_("Port"))),
                            (
                                "proxy_user",
                                TextInput(
                                    title=_("Username"),
                                    size=32,
                                ),
                            ),
                            (
                                "proxy_password",
                                _vs_v1_ssc_password(title=_("Password"), allow_empty=True),
                            ),
                        ],
                        optional_keys=["proxy_port", "proxy_user", "proxy_password"],
                    ),
                ),
                (
                    "access",
                    Dictionary(
                        title=_("Access to AWS API"),
                        elements=[
                            (
                                "global_service_region",
                                DropdownChoice(
                                    title=_("Use custom region for global AWS services"),
                                    choices=[
                                        (None, _("default (all normal AWS regions)")),
                                    ]
                                    + [
                                        (x, x)
                                        for x in (
                                            "us-gov-east-1",
                                            "us-gov-west-1",
                                            "cn-north-1",
                                            "cn-northwest-1",
                                        )
                                    ],
                                    help=_(
                                        "us-gov-* or cn-* regions have their own global services and may not reach the default one."
                                    ),
                                    default_value=None,
                                ),
                            ),
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
                    "regional_services",
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
                (
                    "import_tags",
                    CascadingDropdown(
                        title=("Import tags as host labels"),
                        choices=[
                            (
                                "all_tags",
                                _("Import all valid tags"),
                                FixedValue(None, totext=""),
                            ),
                            (
                                "filter_tags",
                                _("Filter valid tags by key pattern"),
                                RegExp(
                                    mode=RegExp.infix,
                                    allow_empty=False,
                                    size=50,
                                ),
                            ),
                        ],
                        orientation="horizontal",
                        help=_(
                            "Enable this option to import the AWS tags for EC2 and ELB instances "
                            "as host labels for the respective piggyback hosts. The label syntax "
                            "is 'cmk/aws/tag/{key}:{value}'.<br>Additionally, the piggyback hosts "
                            "for EC2 instances are given the host label 'cmk/aws/ec2:instance', "
                            "which is done independent of this option.<br>You can further restrict "
                            "the imported tags by specifying a pattern which Checkmk searches for "
                            "in the key of the AWS tag, or you can disable the import of AWS tags "
                            "altogether."
                        ),
                    ),
                ),
            ],
        ),
        migrate=_migrate,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name=RuleGroup.SpecialAgents("aws"),
        title=lambda: _("Amazon Web Services (AWS)"),
        valuespec=_valuespec_special_agents_aws,
        doc_references={DocReference.AWS: _("Monitoring Amazon Web Services (AWS)")},
    )
)
