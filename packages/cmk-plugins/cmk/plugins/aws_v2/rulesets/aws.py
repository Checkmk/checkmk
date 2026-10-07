#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The rule of the aws_v2 special agent.

The rule is put together from the public builders below. The Quick Setup of the new AWS
integration uses the same builders, so that the rule and the Quick Setup stay the same.
"""

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence
from typing import Final

from cmk.plugins.aws_v2.constants import AWS_REGIONS
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    Integer,
    List,
    MatchingScope,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    RegularExpression,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

_ServiceSpec = tuple[str, Title, Mapping[str, DictElement]]

_GLOBAL_SERVICES: Final[list[_ServiceSpec]] = [
    ("ce", Title("Costs and usage (CE)"), {}),
]

_REGIONAL_SERVICES: Final[list[_ServiceSpec]] = [
    ("ec2", Title("Elastic Compute Cloud (EC2)"), {}),
    ("ebs", Title("Elastic Block Storage (EBS)"), {}),
    (
        "s3",
        Title("Simple Storage Service (S3)"),
        {
            "requests": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Request metrics"),
                    label=Label("Monitor request metrics using the filter EntireBucket"),
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
                ),
                required=True,
            ),
        },
    ),
    ("glacier", Title("Amazon S3 Glacier (Glacier)"), {}),
    ("elb", Title("Classic load balancing (ELB)"), {}),
    ("elbv2", Title("Application and network load balancing (ELBv2)"), {}),
    ("rds", Title("Relational Database Service (RDS)"), {}),
    ("cloudwatch_alarms", Title("CloudWatch alarms"), {}),
    ("dynamodb", Title("DynamoDB"), {}),
    (
        "wafv2",
        Title("Web Application Firewall (WAFV2)"),
        {
            "cloudfront": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("CloudFront WAFs"),
                    label=Label("Monitor CloudFront WAFs"),
                    help_text=Help(
                        "Include WAFs in front of CloudFront resources in the monitoring."
                    ),
                ),
                required=True,
            ),
        },
    ),
]

# These services need the aws_extended license option, and the aws_v2_extended package adds
# them. Their names are also listed here: in an edition without the package, a rule that was
# saved with them must still load.
_EXTENDED_GLOBAL_SERVICE_NAMES: Final = ("route53", "cloudfront")
_EXTENDED_REGIONAL_SERVICE_NAMES: Final = ("aws_lambda", "sns", "ecs", "elasticache")

try:
    from cmk.plugins.aws_v2_extended.rulesets.aws_services import (  # type: ignore[import-not-found]
        EXTENDED_GLOBAL_SERVICES,
        EXTENDED_REGIONAL_SERVICES,
    )

    _GLOBAL_SERVICES.extend(EXTENDED_GLOBAL_SERVICES)
    _REGIONAL_SERVICES.extend(EXTENDED_REGIONAL_SERVICES)
except ImportError:
    pass

_GLOBAL_SERVICE_REGIONS: Final = ("us-gov-east-1", "us-gov-west-1", "cn-north-1", "cn-northwest-1")


def _region_to_formspec_name(region: str) -> str:
    # Form spec names must be Python identifiers.
    return region.replace("-", "_")


def _region_elements() -> Sequence[MultipleChoiceElement]:
    # GovCloud regions go last.
    regions = sorted(AWS_REGIONS, key=lambda region: ("GovCloud" in region[1], region[1]))
    return [
        MultipleChoiceElement(
            name=_region_to_formspec_name(region_id),
            title=Title("%(region_name)s | %(region_id)s")
            % {"region_name": region_name, "region_id": region_id},
        )
        for region_id, region_name in regions
    ]


def _validate_no_aws_prefix(value: str) -> None:
    if value.startswith("aws:"):
        raise validators.ValidationError(Message("Do not use the 'aws:' prefix."))


def _validate_unique_tag_keys(tags: Sequence[Mapping[str, object]]) -> None:
    keys = [tag["key"] for tag in tags]
    if len(keys) != len(set(keys)):
        raise validators.ValidationError(
            Message("Each tag key must be unique and cannot be used multiple times.")
        )


def _tags(title: Title | None = None) -> List:
    return List(
        title=title,
        help_text=Help(
            "For information on AWS tag configuration, visit "
            "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html"
        ),
        element_template=Dictionary(
            elements={
                "key": DictElement(
                    parameter_form=String(
                        title=Title("Key"),
                        custom_validate=(
                            validators.LengthInRange(min_value=1, max_value=128),
                            _validate_no_aws_prefix,
                        ),
                    ),
                    required=True,
                ),
                "values": DictElement(
                    parameter_form=List(
                        element_template=String(
                            label=Label("Value"),
                            custom_validate=(
                                validators.LengthInRange(max_value=256),
                                _validate_no_aws_prefix,
                            ),
                        ),
                        add_element_label=Label("Add new value"),
                        remove_element_label=Label("Remove value"),
                        no_element_label=Label("No values defined"),
                        editable_order=False,
                        custom_validate=(validators.LengthInRange(min_value=1),),
                    ),
                    required=True,
                ),
            },
        ),
        add_element_label=Label("Add new tag"),
        remove_element_label=Label("Remove tag"),
        no_element_label=Label("No tags defined"),
        editable_order=False,
        custom_validate=(
            _validate_unique_tag_keys,
            validators.LengthInRange(
                max_value=50, error_msg=Message("The maximum number of tags per resource is 50.")
            ),
        ),
    )


def _names(label: Label) -> List:
    return List(
        element_template=String(
            label=label, custom_validate=(validators.LengthInRange(min_value=1),)
        ),
        add_element_label=Label("Add new name"),
        remove_element_label=Label("Remove name"),
        no_element_label=Label("No names defined"),
        editable_order=False,
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


def _limits() -> DictElement:
    return DictElement(
        parameter_form=BooleanChoice(
            title=Title("Service limits"),
            label=Label("Monitor service limits"),
            help_text=Help(
                "If limits are monitored, all instances will be fetched "
                "regardless of any name or tag restrictions that may have been "
                "configured."
            ),
            prefill=DefaultValue(True),
        ),
        required=True,
    )


def _service(
    title: Title,
    options: Mapping[str, DictElement],
    *,
    filterable: bool,
    prefill: str,
) -> DictElement:
    elements: list[CascadingSingleChoiceElement] = [
        CascadingSingleChoiceElement(
            name="none",
            title=Title("Do not monitor service"),
            parameter_form=FixedValue(value=None),
        ),
        CascadingSingleChoiceElement(
            name="all",
            title=(
                Title("Gather all service instances and restrict by overall AWS tags")
                if filterable
                else Title("Monitor service")
            ),
            parameter_form=Dictionary(elements=options),
        ),
    ]
    if filterable:
        elements += [
            CascadingSingleChoiceElement(
                name="tags",
                title=Title("Use explicit AWS service tags and overrule overall AWS tags"),
                parameter_form=Dictionary(
                    elements={
                        "tags": DictElement(parameter_form=_tags(), required=True),
                        **options,
                    },
                ),
            ),
            CascadingSingleChoiceElement(
                name="names",
                title=Title("Use explicit service names and ignore overall AWS tags"),
                parameter_form=Dictionary(
                    elements={
                        "names": DictElement(
                            parameter_form=_names(Label("Service name")), required=True
                        ),
                        **options,
                    },
                ),
            ),
        ]
    return DictElement(
        parameter_form=CascadingSingleChoice(
            title=title,
            help_text=Help(
                "<b>Gather all service instances and restrict by overall AWS tags:</b><br>"
                "If overall tags are specified, then all service instances will be "
                "filtered by those tags. Otherwise, all instances will be collected.<br><br>"
                "<b>Use explicit AWS service tags and overrule overall AWS tags:</b><br>"
                "Specify explicit tags for these services. The overall tags will be "
                "ignored for these services.<br><br>"
                "<b>Use explicit service names and ignore overall AWS tags:</b><br>"
                "Use this option to specify explicit names. The overall tags will be "
                "ignored for these services."
            )
            if filterable
            else None,
            elements=elements,
            prefill=DefaultValue(prefill),
        ),
        required=True,
    )


def _cloudwatch_alarms(title: Title) -> DictElement:
    # Alarms are selected by their names only.
    options = {"limits": _limits()}
    return DictElement(
        parameter_form=CascadingSingleChoice(
            title=title,
            elements=[
                CascadingSingleChoiceElement(
                    name="none",
                    title=Title("Do not monitor service"),
                    parameter_form=FixedValue(value=None),
                ),
                CascadingSingleChoiceElement(
                    name="all",
                    title=Title("Gather all"),
                    parameter_form=Dictionary(elements=options),
                ),
                CascadingSingleChoiceElement(
                    name="names",
                    title=Title("Use explicit names"),
                    parameter_form=Dictionary(
                        elements={
                            "names": DictElement(
                                parameter_form=_names(Label("Alarm name")), required=True
                            ),
                            **options,
                        },
                    ),
                ),
            ],
            prefill=DefaultValue("all"),
        ),
        required=True,
    )


def _global_service(name: str, title: Title, options: Mapping[str, DictElement]) -> DictElement:
    # Costs and usage cannot be restricted to tags or names.
    return _service(title, options, filterable=name != "ce", prefill="none")


def _regional_service(name: str, title: Title, options: Mapping[str, DictElement]) -> DictElement:
    if name == "cloudwatch_alarms":
        return _cloudwatch_alarms(title)
    return _service(title, {**options, "limits": _limits()}, filterable=True, prefill="all")


def _access_key() -> Mapping[str, DictElement]:
    return {
        "access_key_id": DictElement(
            parameter_form=String(
                title=Title("The access key ID for your AWS account"),
                field_size=FieldSize.LARGE,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
            required=True,
        ),
        "secret_access_key": DictElement(
            parameter_form=Password(
                title=Title("The secret access key for your AWS account"),
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
            required=True,
        ),
    }


def _assume_role() -> Mapping[str, DictElement]:
    return {
        "role_arn_id": DictElement(
            parameter_form=String(
                title=Title("The ARN of the IAM role to assume"),
                help_text=Help("The Amazon Resource Name (ARN) of the role to assume."),
                field_size=FieldSize.LARGE,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
            required=True,
        ),
        "external_id": DictElement(
            parameter_form=String(
                title=Title("External ID"),
                help_text=Help(
                    "A unique identifier that might be required when you assume a role in another "
                    "account. If the administrator of the account to which the role belongs provided "
                    "you with an external ID, then provide that value in the External ID parameter. "
                ),
                field_size=FieldSize.LARGE,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
        ),
    }


def configuration_authentication() -> Mapping[str, DictElement]:
    return {
        "auth": DictElement(
            parameter_form=CascadingSingleChoice(
                title=Title("Authentication type"),
                help_text=Help(
                    "Monitoring via an IAM role is recommended, however it requires the monitoring "
                    "site to be located on an AWS EC2 instance with the according permissions to "
                    "the accounts to be monitored."
                ),
                elements=[
                    CascadingSingleChoiceElement(
                        name="access_key",
                        title=Title("Access key"),
                        parameter_form=Dictionary(elements=_access_key()),
                    ),
                    CascadingSingleChoiceElement(
                        name="access_key_sts",
                        title=Title("Access key + IAM role"),
                        parameter_form=Dictionary(elements={**_access_key(), **_assume_role()}),
                    ),
                    CascadingSingleChoiceElement(
                        name="sts",
                        title=Title("IAM role (on EC2 instance only)"),
                        parameter_form=Dictionary(elements=_assume_role()),
                    ),
                    CascadingSingleChoiceElement(
                        name="none",
                        title=Title("None (on EC2 instance only)"),
                        parameter_form=FixedValue(value=None),
                    ),
                ],
                prefill=DefaultValue("access_key"),
            ),
            required=True,
        ),
        "global_service_region": DictElement(
            parameter_form=SingleChoice(
                title=Title("Use custom region for global AWS services"),
                help_text=Help(
                    "us-gov-* or cn-* regions have their own global services and may not reach "
                    "the default one."
                ),
                elements=[
                    SingleChoiceElement(
                        name="default", title=Title("default (all normal AWS regions)")
                    ),
                    *(
                        SingleChoiceElement(
                            name=_region_to_formspec_name(region),
                            title=Title("%(region)s") % {"region": region},
                        )
                        for region in _GLOBAL_SERVICE_REGIONS
                    ),
                ],
                prefill=DefaultValue("default"),
            ),
            required=True,
        ),
        "proxy_details": DictElement(
            parameter_form=Dictionary(
                title=Title("Proxy server details"),
                elements={
                    "proxy_host": DictElement(
                        parameter_form=String(
                            title=Title("Proxy host"),
                            custom_validate=(validators.LengthInRange(min_value=1),),
                        ),
                        required=True,
                    ),
                    "proxy_port": DictElement(
                        parameter_form=Integer(
                            title=Title("Port"),
                            custom_validate=(validators.NetworkPort(),),
                        ),
                    ),
                    "proxy_user": DictElement(
                        parameter_form=String(
                            title=Title("Username"),
                            custom_validate=(validators.LengthInRange(min_value=1),),
                        ),
                    ),
                    "proxy_password": DictElement(
                        parameter_form=Password(title=Title("Password")),
                    ),
                },
            ),
        ),
    }


def configuration_regions_and_tags() -> Mapping[str, DictElement]:
    return {
        "regions": DictElement(
            parameter_form=MultipleChoice(
                title=Title("Regions to monitor"),
                elements=_region_elements(),
            ),
            required=True,
        ),
        "overall_tags": DictElement(
            parameter_form=_tags(Title("Restrict monitoring services by one of these AWS tags")),
        ),
        "import_tags": DictElement(
            parameter_form=CascadingSingleChoice(
                title=Title("Import tags as host labels"),
                help_text=Help(
                    "Enable this option to import the AWS tags for EC2 and ELB instances "
                    "as host labels for the respective piggyback hosts. The label syntax "
                    "is 'cmk/aws/tag/{key}:{value}'.<br>Additionally, the piggyback hosts "
                    "for EC2 instances are given the host label 'cmk/aws/ec2:instance', "
                    "which is done independent of this option.<br>You can further restrict "
                    "the imported tags by specifying a pattern which Checkmk searches for "
                    "in the key of the AWS tag, or you can disable the import of AWS tags "
                    "altogether."
                ),
                elements=[
                    CascadingSingleChoiceElement(
                        name="all_tags",
                        title=Title("Import all valid tags"),
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="filter_tags",
                        title=Title("Filter valid tags by key pattern"),
                        parameter_form=RegularExpression(
                            predefined_help_text=MatchingScope.INFIX,
                            custom_validate=(validators.LengthInRange(min_value=1),),
                        ),
                    ),
                    CascadingSingleChoiceElement(
                        name="ignore_tags",
                        title=Title("Do not import tags"),
                        parameter_form=FixedValue(value=None),
                    ),
                ],
                prefill=DefaultValue("all_tags"),
            ),
            required=True,
        ),
    }


def _not_configurable(names: Sequence[str], elements: Mapping[str, DictElement]) -> tuple[str, ...]:
    return tuple(name for name in names if name not in elements)


def configuration_services() -> Mapping[str, DictElement]:
    global_services = {
        name: _global_service(name, title, options) for name, title, options in _GLOBAL_SERVICES
    }
    regional_services = {
        name: _regional_service(name, title, options) for name, title, options in _REGIONAL_SERVICES
    }
    return {
        "global_services": DictElement(
            parameter_form=Dictionary(
                title=Title("Global services to monitor"),
                elements=global_services,
                ignored_elements=_not_configurable(_EXTENDED_GLOBAL_SERVICE_NAMES, global_services),
            ),
            required=True,
        ),
        "regional_services": DictElement(
            parameter_form=Dictionary(
                title=Title("Services per region to monitor"),
                elements=regional_services,
                ignored_elements=_not_configurable(
                    _EXTENDED_REGIONAL_SERVICE_NAMES, regional_services
                ),
            ),
            required=True,
        ),
    }


def configuration_piggyback_naming() -> Mapping[str, DictElement]:
    return {
        "piggyback_naming_convention": DictElement(
            parameter_form=SingleChoice(
                title=Title("Piggyback names"),
                help_text=Help(
                    "Each EC2 instance creates a piggyback host.<br><b>Note:</b> "
                    "Not every host name is pingable and changing the piggyback name "
                    "will reset the piggyback host.<br><br><b>IP - Region - Instance "
                    'ID:</b><br>The name consists of "{Private IPv4 '
                    'address}-{Region}-{Instance ID}". This uniquely identifies the '
                    "EC2 instance. It is not possible to ping this host name."
                ),
                elements=[
                    SingleChoiceElement(
                        name="ip_region_instance", title=Title("IP - region - instance ID")
                    ),
                    SingleChoiceElement(
                        name="private_dns_name", title=Title("Private IP DNS name")
                    ),
                ],
                prefill=DefaultValue("ip_region_instance"),
            ),
            required=True,
        ),
    }


def formspec() -> Dictionary:
    return Dictionary(
        elements={
            **configuration_authentication(),
            **configuration_regions_and_tags(),
            **configuration_services(),
            **configuration_piggyback_naming(),
        },
    )


rule_spec_aws_v2 = SpecialAgent(
    name="aws_v2",
    title=Title("Amazon Web Services (AWS) v2"),  # TODO: Change this once we deprecate the old one
    topic=Topic.CLOUD,
    parameter_form=formspec,
)
