#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from cmk.gui.form_specs.generators.age import Age
from cmk.gui.form_specs.generators.alternative_utils import enable_deprecated_alternative
from cmk.gui.form_specs.unstable import CascadingSingleChoiceExtended
from cmk.gui.form_specs.unstable.cascading_single_choice_extended import (
    CascadingSingleChoiceElementExtended,
)
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.gui.form_specs.unstable.legacy_converter.generators import TupleLevels
from cmk.plugins.aws.constants import (  # pylint: disable=cmk-module-layer-violation
    AWSEC2InstFamilies,
    AWSEC2InstTypes,
    AWSEC2LimitsDefault,
    AWSEC2LimitsSpecial,
)
from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    FormSpec,
    IECMagnitude,
    Integer,
    List,
    Percentage,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, HostCondition, Topic
from cmk.shared_typing.vue_formspec_components import CascadingSingleChoiceLayout


def _fs_s3_buckets() -> Mapping[str, DictElement]:
    return {
        "bucket_size_levels": DictElement(
            parameter_form=enable_deprecated_alternative(
                wrapped_form_spec=CascadingSingleChoice(
                    title=Title("Upper levels for the bucket size"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="alternative_levels",
                            title=Title("Set levels"),
                            parameter_form=TupleLevels(
                                title=Title("Set levels"),
                                elements=[
                                    DataSize(
                                        title=Title("Warning at"),
                                        displayed_magnitudes=(
                                            IECMagnitude.BYTE,
                                            IECMagnitude.KIBI,
                                            IECMagnitude.MEBI,
                                            IECMagnitude.GIBI,
                                            IECMagnitude.TEBI,
                                        ),
                                    ),
                                    DataSize(
                                        title=Title("Critical at"),
                                        displayed_magnitudes=(
                                            IECMagnitude.BYTE,
                                            IECMagnitude.KIBI,
                                            IECMagnitude.MEBI,
                                            IECMagnitude.GIBI,
                                            IECMagnitude.TEBI,
                                        ),
                                    ),
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="alternative_no_levels",
                            title=Title("No levels"),
                            parameter_form=TupleLevels(
                                title=Title("No levels"),
                                elements=[
                                    FixedValue(value=None),
                                    FixedValue(value=None),
                                ],
                            ),
                        ),
                    ],
                )
            ),
        )
    }


def _fs_glacier_vaults() -> Mapping[str, DictElement]:
    return {
        "vault_size_levels": DictElement(
            parameter_form=enable_deprecated_alternative(
                wrapped_form_spec=CascadingSingleChoice(
                    title=Title("Upper levels for the vault size"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="alternative_levels",
                            title=Title("Set levels"),
                            parameter_form=TupleLevels(
                                title=Title("Set levels"),
                                elements=[
                                    DataSize(
                                        title=Title("Warning at"),
                                        displayed_magnitudes=(
                                            IECMagnitude.BYTE,
                                            IECMagnitude.KIBI,
                                            IECMagnitude.MEBI,
                                            IECMagnitude.GIBI,
                                            IECMagnitude.TEBI,
                                        ),
                                    ),
                                    DataSize(
                                        title=Title("Critical at"),
                                        displayed_magnitudes=(
                                            IECMagnitude.BYTE,
                                            IECMagnitude.KIBI,
                                            IECMagnitude.MEBI,
                                            IECMagnitude.GIBI,
                                            IECMagnitude.TEBI,
                                        ),
                                    ),
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="alternative_no_levels",
                            title=Title("No levels"),
                            parameter_form=TupleLevels(
                                title=Title("No levels"),
                                elements=[
                                    FixedValue(value=None),
                                    FixedValue(value=None),
                                ],
                            ),
                        ),
                    ],
                )
            ),
        )
    }


def _fs_burst_balance() -> Mapping[str, DictElement]:
    return {
        "burst_balance_levels_lower": DictElement(
            parameter_form=enable_deprecated_alternative(
                wrapped_form_spec=CascadingSingleChoice(
                    title=Title("Lower levels for burst balance"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="alternative_levels",
                            title=Title("Set levels"),
                            parameter_form=TupleLevels(
                                title=Title("Set levels"),
                                elements=[
                                    Percentage(title=Title("Warning at or below")),
                                    Percentage(title=Title("Critical at or below")),
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="alternative_no_levels",
                            title=Title("No levels"),
                            parameter_form=TupleLevels(
                                title=Title("No levels"),
                                elements=[
                                    FixedValue(value=None),
                                    FixedValue(value=None),
                                ],
                            ),
                        ),
                    ],
                )
            ),
        )
    }


def _fs_cpu_credits_balance():
    return {
        "balance_levels_lower": DictElement(
            parameter_form=enable_deprecated_alternative(
                wrapped_form_spec=CascadingSingleChoice(
                    title=Title("Lower levels for CPU balance"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="alternative_levels",
                            title=Title("Set levels"),
                            parameter_form=TupleLevels(
                                title=Title("Set levels"),
                                elements=[
                                    Integer(title=Title("Warning at or below")),
                                    Integer(title=Title("Critical at or below")),
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="alternative_no_levels",
                            title=Title("No levels"),
                            parameter_form=TupleLevels(
                                title=Title("No levels"),
                                elements=[
                                    FixedValue(value=None),
                                    FixedValue(value=None),
                                ],
                            ),
                        ),
                    ],
                )
            )
        )
    }


def _fs_elements_http_errors(
    http_err_codes: Iterable[str],
    title_add: Callable[[str], Title] = lambda http_err_code: Title(""),
) -> Mapping[str, DictElement]:
    return {
        "levels_http_%s_perc" % http_err_code: DictElement(
            parameter_form=TupleLevels(
                title=Title(f"Upper percentual levels for HTTP {http_err_code.upper()} errors")  # pylint: disable=localization-of-non-literal-string
                + title_add(http_err_code),
                help_text=Help(  # pylint: disable=localization-of-non-literal-string
                    f"Specify levels for HTTP {http_err_code.upper()} errors in percent "
                    "which refer to the total number of requests."
                ),
                elements=[
                    Percentage(title=Title("Warning at")),
                    Percentage(title=Title("Critical at")),
                ],
            ),
        )
        for http_err_code in http_err_codes
    }


def _fs_latency() -> Mapping[str, DictElement]:
    return {
        "levels_latency": DictElement(
            parameter_form=TupleLevels(
                title=Title("Upper levels for latency"), elements=[Age(), Age()]
            ),
        )
    }


def _item_spec_aws_limits_generic():
    return String(
        title=Title("Region name"), help_text=Help("An AWS region name such as 'eu-central-1'")
    )


def fs_aws_limits(
    resource: Title,
    default_limit: int,
    fs_limit_cls: type[DataSize] | None = None,
    unit: str = "",
    title_default: Title = Title("Limit from AWS API"),
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    fs_limit: Integer | DataSize
    if fs_limit_cls is None:
        fs_limit = Integer(
            title=resource,
            unit_symbol=unit,
            prefill=DefaultValue(default_limit),
            custom_validate=[
                validators.NumberInRange(
                    min_value=1, error_msg=Message("Integer field can not be empty")
                )
            ],
        )
    else:
        fs_limit = fs_limit_cls(
            title=resource,
            prefill=DefaultValue(default_limit),
            displayed_magnitudes=(
                IECMagnitude.BYTE,
                IECMagnitude.KIBI,
                IECMagnitude.MEBI,
                IECMagnitude.GIBI,
                IECMagnitude.TEBI,
            ),
            custom_validate=[
                validators.NumberInRange(
                    min_value=1, error_msg=Message("Integer field can not be empty")
                )
            ],
        )

    return enable_deprecated_alternative(
        wrapped_form_spec=CascadingSingleChoice(
            title=resource,
            elements=[
                CascadingSingleChoiceElement(
                    name="alternative_levels",
                    title=Title("Set levels"),
                    parameter_form=Tuple(
                        layout="vertical",
                        elements=[
                            enable_deprecated_alternative(
                                wrapped_form_spec=CascadingSingleChoiceExtended(
                                    layout=CascadingSingleChoiceLayout.horizontal,
                                    elements=[
                                        CascadingSingleChoiceElement(
                                            name="no_limit",
                                            title=title_default,
                                            parameter_form=FixedValue(
                                                value=None,
                                            ),
                                        ),
                                        CascadingSingleChoiceElement(
                                            title=resource,
                                            name="with_limit",
                                            parameter_form=fs_limit,
                                        ),
                                    ],
                                )
                            ),
                            Percentage(title=Title("Warning at"), prefill=DefaultValue(80.0)),
                            Percentage(title=Title("Critical at"), prefill=DefaultValue(90.0)),
                        ],
                    ),
                ),
                CascadingSingleChoiceElement(
                    name="alternative_no_levels",
                    title=Title("No levels"),
                    parameter_form=Tuple(
                        title=Title("No levels"),
                        elements=[
                            FixedValue(value=None),
                            FixedValue(value=None),
                            FixedValue(value=None),
                        ],
                    ),
                ),
            ],
        )
    )


# .
#   .--Glacier-------------------------------------------------------------.
#   |                    ____ _            _                               |
#   |                   / ___| | __ _  ___(_) ___ _ __                     |
#   |                  | |  _| |/ _` |/ __| |/ _ \ '__|                    |
#   |                  | |_| | | (_| | (__| |  __/ |                       |
#   |                   \____|_|\__,_|\___|_|\___|_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_form_spec_aws_glacier_vaults():
    return Dictionary(elements=_fs_glacier_vaults())


rule_spec_aws_glacier_vault_archives = CheckParameters(
    name="aws_glacier_vault_archives",
    title=Title("AWS/Glacier Vault Objects"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_glacier_vaults,
    condition=HostAndItemCondition(item_title=Title("Vault name")),
)


rule_spec_aws_glacier_vaults = CheckParameters(
    name="aws_glacier_vaults",
    title=Title("AWS/Glacier Vaults"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_glacier_vaults,
    condition=HostCondition(),
)


def _parameter_form_spec_aws_glacier_limits() -> Dictionary:
    return Dictionary(
        elements={
            "number_of_vaults": DictElement(
                parameter_form=fs_aws_limits(Title("Vaults"), 1000),
            )
        }
    )


rule_spec_aws_glacier_limits = CheckParameters(
    name="aws_glacier_limits",
    title=Title("AWS/Glacier Limits"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_glacier_limits,
    condition=HostAndItemCondition(
        item_title=Title("Region name"), item_form=_item_spec_aws_limits_generic()
    ),
)

#   .--S3------------------------------------------------------------------.


def _parameter_form_spec_aws_s3_buckets() -> Dictionary:
    return Dictionary(elements=_fs_s3_buckets())


rule_spec_aws_s3_buckets_objects = CheckParameters(
    name="aws_s3_buckets_objects",
    title=Title("AWS/S3 Bucket Objects"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_s3_buckets,
    condition=HostAndItemCondition(item_title=Title("Bucket name")),
)


rule_spec_aws_s3_buckets = CheckParameters(
    name="aws_s3_buckets",
    title=Title("AWS/S3 Buckets"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_s3_buckets,
    condition=HostCondition(),
)


def _parameter_form_spec_aws_s3_requests() -> Dictionary:
    return Dictionary(
        elements={
            "get_requests_perc": DictElement(
                parameter_form=enable_deprecated_alternative(
                    wrapped_form_spec=CascadingSingleChoice(
                        title=Title("Upper percentual levels for GET requests"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="alternative_levels",
                                title=Title("Set levels"),
                                parameter_form=TupleLevels(
                                    title=Title("Set levels"),
                                    elements=[
                                        Percentage(title=Title("Warning at")),
                                        Percentage(title=Title("Critical at")),
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="alternative_no_levels",
                                title=Title("No levels"),
                                parameter_form=TupleLevels(
                                    title=Title("No levels"),
                                    elements=[
                                        FixedValue(value=None),
                                        FixedValue(value=None),
                                    ],
                                ),
                            ),
                        ],
                    )
                ),
            ),
            "put_requests_perc": DictElement(
                parameter_form=enable_deprecated_alternative(
                    wrapped_form_spec=CascadingSingleChoice(
                        title=Title("Upper percentual levels for PUT requests"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="alternative_levels",
                                title=Title("Set levels"),
                                parameter_form=TupleLevels(
                                    title=Title("Set levels"),
                                    elements=[
                                        Percentage(title=Title("Warning at")),
                                        Percentage(title=Title("Critical at")),
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="alternative_no_levels",
                                title=Title("No levels"),
                                parameter_form=TupleLevels(
                                    title=Title("No levels"),
                                    elements=[
                                        FixedValue(value=None),
                                        FixedValue(value=None),
                                    ],
                                ),
                            ),
                        ],
                    )
                ),
            ),
            "delete_requests_perc": DictElement(
                parameter_form=enable_deprecated_alternative(
                    wrapped_form_spec=CascadingSingleChoice(
                        title=Title("Upper percentual levels for DELETE requests"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="alternative_levels",
                                title=Title("Set levels"),
                                parameter_form=TupleLevels(
                                    title=Title("Set levels"),
                                    elements=[
                                        Percentage(title=Title("Warning at")),
                                        Percentage(title=Title("Critical at")),
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="alternative_no_levels",
                                title=Title("No levels"),
                                parameter_form=TupleLevels(
                                    title=Title("No levels"),
                                    elements=[
                                        FixedValue(value=None),
                                        FixedValue(value=None),
                                    ],
                                ),
                            ),
                        ],
                    )
                ),
            ),
            "head_requests_perc": DictElement(
                parameter_form=enable_deprecated_alternative(
                    wrapped_form_spec=CascadingSingleChoice(
                        title=Title("Upper percentual levels for HEAD requests"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="alternative_levels",
                                title=Title("Set levels"),
                                parameter_form=TupleLevels(
                                    title=Title("Set levels"),
                                    elements=[
                                        Percentage(title=Title("Warning at")),
                                        Percentage(title=Title("Critical at")),
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="alternative_no_levels",
                                title=Title("No levels"),
                                parameter_form=TupleLevels(
                                    title=Title("No levels"),
                                    elements=[
                                        FixedValue(value=None),
                                        FixedValue(value=None),
                                    ],
                                ),
                            ),
                        ],
                    )
                ),
            ),
            "post_requests_perc": DictElement(
                parameter_form=enable_deprecated_alternative(
                    wrapped_form_spec=CascadingSingleChoice(
                        title=Title("Upper percentual levels for POST requests"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="alternative_levels",
                                title=Title("Set levels"),
                                parameter_form=TupleLevels(
                                    title=Title("Set levels"),
                                    elements=[
                                        Percentage(title=Title("Warning at")),
                                        Percentage(title=Title("Critical at")),
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="alternative_no_levels",
                                title=Title("No levels"),
                                parameter_form=TupleLevels(
                                    title=Title("No levels"),
                                    elements=[
                                        FixedValue(value=None),
                                        FixedValue(value=None),
                                    ],
                                ),
                            ),
                        ],
                    )
                ),
            ),
            "select_requests_perc": DictElement(
                parameter_form=enable_deprecated_alternative(
                    wrapped_form_spec=CascadingSingleChoice(
                        title=Title("Upper percentual levels for SELECT requests"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="alternative_levels",
                                title=Title("Set levels"),
                                parameter_form=TupleLevels(
                                    title=Title("Set levels"),
                                    elements=[
                                        Percentage(title=Title("Warning at")),
                                        Percentage(title=Title("Critical at")),
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="alternative_no_levels",
                                title=Title("No levels"),
                                parameter_form=TupleLevels(
                                    title=Title("No levels"),
                                    elements=[
                                        FixedValue(value=None),
                                        FixedValue(value=None),
                                    ],
                                ),
                            ),
                        ],
                    )
                ),
            ),
            "list_requests_perc": DictElement(
                parameter_form=enable_deprecated_alternative(
                    wrapped_form_spec=CascadingSingleChoice(
                        title=Title("Upper percentual levels for LIST requests"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="alternative_levels",
                                title=Title("Set levels"),
                                parameter_form=TupleLevels(
                                    title=Title("Set levels"),
                                    elements=[
                                        Percentage(title=Title("Warning at")),
                                        Percentage(title=Title("Critical at")),
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="alternative_no_levels",
                                title=Title("No levels"),
                                parameter_form=TupleLevels(
                                    title=Title("No levels"),
                                    elements=[
                                        FixedValue(value=None),
                                        FixedValue(value=None),
                                    ],
                                ),
                            ),
                        ],
                    )
                ),
            ),
        }
    )


rule_spec_aws_s3_requests = CheckParameters(
    name="aws_s3_requests",
    title=Title("AWS/S3 Bucket Requests"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_s3_requests,
    condition=HostAndItemCondition(item_title=Title("Bucket name")),
)


def _parameter_form_spec_aws_s3_latency() -> Dictionary:
    return Dictionary(
        title=Title("Levels on latency"),
        elements={
            "levels_seconds": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper levels on total request latency"),
                    elements=[
                        Float(title=Title("Warning at"), unit_symbol="ms"),
                        Float(title=Title("Critical at"), unit_symbol="ms"),
                    ],
                ),
            )
        },
    )


rule_spec_aws_s3_latency = CheckParameters(
    name="aws_s3_latency",
    title=Title("AWS/S3 Latency"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_s3_latency,
    condition=HostAndItemCondition(item_title=Title("Bucket name")),
)


def _parameter_form_spec_aws_s3_limits() -> Dictionary:
    return Dictionary(
        elements={
            "buckets": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Buckets"), 100, title_default=Title("Default limit set by AWS")
                ),
            )
        }
    )


rule_spec_aws_s3_limits = CheckParameters(
    name="aws_s3_limits",
    title=Title("AWS/S3 Limits"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_s3_limits,
    condition=HostAndItemCondition(
        item_title=Title("Region name"), item_form=_item_spec_aws_limits_generic()
    ),
)


def _parameter_form_spec_aws_s3_http_errors():
    return Dictionary(
        title=Title("Upper levels for HTTP errors"),
        elements=_fs_elements_http_errors(["4xx", "5xx"]),
    )


rule_spec_aws_s3_http_errors = CheckParameters(
    name="aws_s3_http_errors",
    title=Title("AWS/S3 HTTP Errors"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_s3_http_errors,
    condition=HostAndItemCondition(item_title=Title("Bucket name")),
)

# .
#   .--EC2-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____/ ___|___ \                            |
#   |                         |  _|| |     __) |                           |
#   |                         | |__| |___ / __/                            |
#   |                         |_____\____|_____|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_form_spec_aws_ec2_cpu_credits() -> Dictionary:
    return Dictionary(elements=_fs_cpu_credits_balance())


rule_spec_aws_ec2_cpu_credits = CheckParameters(
    name="aws_ec2_cpu_credits",
    title=Title("AWS/EC2 CPU Credits"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_ec2_cpu_credits,
    condition=HostCondition(),
)


def _vs_limits_inst_types() -> List:
    return List(
        element_template=CascadingSingleChoiceExtended(
            layout=CascadingSingleChoiceLayout.horizontal,
            elements=[
                CascadingSingleChoiceElementExtended(
                    name=inst_type,
                    title=Title(inst_type),  # pylint: disable=localization-of-non-literal-string
                    parameter_form=fs_aws_limits(
                        Title("%s instances") % inst_type,
                        AWSEC2LimitsSpecial.get(inst_type, AWSEC2LimitsDefault)[0],
                    ),
                )
                for inst_type in AWSEC2InstTypes
            ],
        ),
        title=Title("Set limits and levels for running on-demand instances"),
    )


def _vs_limits_vcpu_families() -> List:
    return List(
        element_template=CascadingSingleChoiceExtended(
            layout=CascadingSingleChoiceLayout.horizontal,
            elements=[
                CascadingSingleChoiceElementExtended(
                    name="%s_vcpu" % inst_fam,
                    title=fam_name,
                    parameter_form=fs_aws_limits(
                        fam_name,
                        AWSEC2LimitsSpecial.get("%s_vcpu" % inst_fam, AWSEC2LimitsDefault)[0],
                    ),
                )
                for inst_fam, fam_name in AWSEC2InstFamilies.items()
            ],
        ),
        title=Title("Set limits and levels for running on-demand vCPUs on instance families"),
    )


def _parameter_form_spec_aws_ec2_limits() -> Dictionary:
    return Dictionary(
        elements={
            "vpc_elastic_ip_addresses": DictElement(
                parameter_form=fs_aws_limits(Title("VPC Elastic IP addresses"), 5)
            ),
            "elastic_ip_addresses": DictElement(
                parameter_form=fs_aws_limits(Title("Elastic IP addresses"), 5)
            ),
            "vpc_sec_group_rules": DictElement(
                parameter_form=fs_aws_limits(Title("Rules of VPC security group"), 120),
            ),
            "vpc_sec_groups": DictElement(
                parameter_form=fs_aws_limits(Title("VPC security groups"), 2500)
            ),
            "if_vpc_sec_group": DictElement(
                parameter_form=fs_aws_limits(
                    Title("VPC security groups of elastic network interface"), 5
                ),
            ),
            "spot_inst_requests": DictElement(
                parameter_form=fs_aws_limits(Title("Spot Instance Requests"), 20)
            ),
            "active_spot_fleet_requests": DictElement(
                parameter_form=fs_aws_limits(Title("Active Spot Fleet Requests"), 1000),
            ),
            "spot_fleet_total_target_capacity": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Spot Fleet Requests Total Target Capacity"), 5000
                ),
            ),
            "running_ondemand_instances_total": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Total Running On-Demand Instances(Deprecated by AWS)"), 20
                ),
            ),
            "running_ondemand_instances_vcpus": DictElement(
                parameter_form=_vs_limits_vcpu_families()
            ),
            "running_ondemand_instances": DictElement(parameter_form=_vs_limits_inst_types()),
        }
    )


rule_spec_aws_ec2_limits = CheckParameters(
    name="aws_ec2_limits",
    title=Title("AWS/EC2 Limits"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_ec2_limits,
    condition=HostAndItemCondition(
        item_title=Title("Region name"), item_form=_item_spec_aws_limits_generic()
    ),
)

# .
#   .--CE------------------------------------------------------------------.
#   |                              ____ _____                              |
#   |                             / ___| ____|                             |
#   |                            | |   |  _|                               |
#   |                            | |___| |___                              |
#   |                             \____|_____|                             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_form_spec_aws_costs_and_usage() -> Dictionary:
    return Dictionary(
        elements={
            "levels_unblended": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper levels for unblended costs"),
                    elements=[
                        Integer(title=Title("Warning at USD per day")),
                        Integer(title=Title("Critical at USD per day")),
                    ],
                ),
            )
        }
    )


rule_spec_aws_costs_and_usage = CheckParameters(
    name="aws_costs_and_usage",
    title=Title("AWS/CE Costs and Usage"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_costs_and_usage,
    condition=HostAndItemCondition(item_title=Title("Service name")),
)


def _parameter_form_spec_aws_reservation_utilization() -> Dictionary:
    return Dictionary(
        elements={
            "levels_utilization_percent": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Lower levels for reservation utilization"),
                    elements=[
                        Percentage(title=Title("Warning at"), prefill=DefaultValue(95.0)),
                        Percentage(title=Title("Critical at"), prefill=DefaultValue(90.0)),
                    ],
                ),
            )
        }
    )


rule_spec_aws_reservation_utilization = CheckParameters(
    name="aws_reservation_utilization",
    title=Title("AWS/CE Total Reservation Utilization"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_reservation_utilization,
    condition=HostCondition(),
)

# .
#   .--ELB-----------------------------------------------------------------.
#   |                          _____ _     ____                            |
#   |                         | ____| |   | __ )                           |
#   |                         |  _| | |   |  _ \                           |
#   |                         | |___| |___| |_) |                          |
#   |                         |_____|_____|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_form_spec_aws_elb_statistics() -> Dictionary:
    return Dictionary(
        elements={
            "levels_surge_queue_length": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper levels for surge queue length"),
                    elements=[
                        Integer(title=Title("Warning at"), prefill=DefaultValue(1024)),
                        Integer(title=Title("Critical at"), prefill=DefaultValue(1024)),
                    ],
                ),
            ),
            "levels_spillover": DictElement(
                parameter_form=TupleLevels(
                    title=Title(
                        "Upper levels for the number of requests that were rejected (spillover)"
                    ),
                    elements=[
                        Float(
                            title=Title("Warning at"), prefill=DefaultValue(0.001), unit_symbol="/s"
                        ),
                        Float(
                            title=Title("Critical at"),
                            prefill=DefaultValue(0.001),
                            unit_symbol="/s",
                        ),
                    ],
                ),
            ),
        }
    )


rule_spec_aws_elb_statistics = CheckParameters(
    name="aws_elb_statistics",
    title=Title("AWS/ELB Statistics"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_elb_statistics,
    condition=HostCondition(),
)


def _parameter_form_spec_aws_elb_latency() -> Dictionary:
    return Dictionary(elements=_fs_latency())


rule_spec_aws_elb_latency = CheckParameters(
    name="aws_elb_latency",
    title=Title("AWS/ELB Latency"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_elb_latency,
    condition=HostCondition(),
)


def _parameter_form_spec_aws_elb_http() -> Dictionary:
    return Dictionary(
        title=Title("Upper levels for HTTP errors"),
        elements={
            "levels_load_balancers": DictElement(
                parameter_form=Dictionary(
                    title=Title("Upper levels for Load Balancers"),
                    elements=_fs_elements_http_errors(
                        ["3xx", "4xx", "5xx", "500", "502", "503", "504"],
                        title_add=lambda http_err_code: (
                            Title("")
                            if http_err_code in ["4xx", "5xx"]
                            else Title(" (Application Load Balancers only)")
                        ),
                    ),
                ),
            ),
            "levels_backend_targets": DictElement(
                parameter_form=Dictionary(
                    title=Title("Upper levels for Backend"),
                    elements=_fs_elements_http_errors(["2xx", "3xx", "4xx", "5xx"]),
                ),
            ),
        },
    )


rule_spec_aws_elb_http = CheckParameters(
    name="aws_elb_http",
    title=Title("AWS/ELB HTTP Errors"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_elb_http,
    condition=HostCondition(),
)


def _parameter_form_spec_aws_elb_healthy_hosts() -> Dictionary:
    return Dictionary(
        elements={
            "levels_overall_hosts_health_perc": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper percentual levels for healthy hosts"),
                    help_text=Help(
                        "These levels refer to the total number of instances or hosts "
                        "that are registered to the load balancer which is the sum of "
                        "healthy and unhealthy instances."
                    ),
                    elements=[
                        Percentage(title=Title("Warning at")),
                        Percentage(title=Title("Critical at")),
                    ],
                ),
            )
        }
    )


rule_spec_aws_elb_healthy_hosts = CheckParameters(
    name="aws_elb_healthy_hosts",
    title=Title("AWS/ELB Healthy Hosts"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_elb_healthy_hosts,
    condition=HostCondition(),
)


def _parameter_form_spec_aws_elb_backend_connection_errors():
    return Dictionary(
        elements={
            "levels_backend_connections_errors_rate": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper levels for backend connection errors per second"),
                    elements=[
                        Float(title=Title("Warning at"), unit_symbol="/s"),
                        Float(title=Title("Critical at"), unit_symbol="/s"),
                    ],
                ),
            )
        }
    )


rule_spec_aws_elb_backend_connection_errors = CheckParameters(
    name="aws_elb_backend_connection_errors",
    title=Title("AWS/ELB back-end connection errors"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_elb_backend_connection_errors,
    condition=HostCondition(),
)


def _parameter_form_spec_aws_elb_limits() -> Dictionary:
    return Dictionary(
        elements={
            "load_balancers": DictElement(
                parameter_form=fs_aws_limits(Title("Load balancers"), 20),
            ),
            "load_balancer_listeners": DictElement(
                parameter_form=fs_aws_limits(Title("Listeners per load balancer"), 100),
            ),
            "load_balancer_registered_instances": DictElement(
                parameter_form=fs_aws_limits(Title("Registered instances per load balancer"), 1000),
            ),
        }
    )


rule_spec_aws_elb_limits = CheckParameters(
    name="aws_elb_limits",
    title=Title("AWS/ELB Limits"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_elb_limits,
    condition=HostAndItemCondition(
        item_title=Title("Region name"), item_form=_item_spec_aws_limits_generic()
    ),
)

# .
#   .--ELBv2---------------------------------------------------------------.
#   |                    _____ _     ____       ____                       |
#   |                   | ____| |   | __ )_   _|___ \                      |
#   |                   |  _| | |   |  _ \ \ / / __) |                     |
#   |                   | |___| |___| |_) \ V / / __/                      |
#   |                   |_____|_____|____/ \_/ |_____|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_form_spec_aws_elbv2_limits() -> Dictionary:
    return Dictionary(
        elements={
            "application_load_balancers": DictElement(
                parameter_form=fs_aws_limits(Title("Application Load balancers"), 20),
            ),
            "application_load_balancer_rules": DictElement(
                parameter_form=fs_aws_limits(Title("Application Load Balancer Rules"), 100),
            ),
            "application_load_balancer_listeners": DictElement(
                parameter_form=fs_aws_limits(Title("Application Load Balancer Listeners"), 50),
            ),
            "application_load_balancer_target_groups": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Application Load Balancer Target Groups"), 3000
                ),
            ),
            "application_load_balancer_certificates": DictElement(
                parameter_form=fs_aws_limits(Title("Application Load balancer Certificates"), 25),
            ),
            "network_load_balancers": DictElement(
                parameter_form=fs_aws_limits(Title("Network Load balancers"), 20)
            ),
            "network_load_balancer_listeners": DictElement(
                parameter_form=fs_aws_limits(Title("Network Load Balancer Listeners"), 50),
            ),
            "network_load_balancer_target_groups": DictElement(
                parameter_form=fs_aws_limits(Title("Network Load Balancer Target Groups"), 3000),
            ),
            "load_balancer_target_groups": DictElement(
                parameter_form=fs_aws_limits(Title("Load balancers target groups"), 3000),
            ),
        }
    )


rule_spec_aws_elbv2_limits = CheckParameters(
    name="aws_elbv2_limits",
    title=Title("AWS/ELBv2 Limits"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_elbv2_limits,
    condition=HostAndItemCondition(
        item_title=Title("Region name"), item_form=_item_spec_aws_limits_generic()
    ),
)


def _parameter_form_spec_aws_elbv2_lcu() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper levels for load balancer capacity units"),
                    elements=[Float(title=Title("Warning at")), Float(title=Title("Critical at"))],
                ),
            )
        }
    )


rule_spec_aws_elbv2_lcu = CheckParameters(
    name="aws_elbv2_lcu",
    title=Title("AWS/ELBv2 LCU"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_elbv2_lcu,
    condition=HostCondition(),
)


def _parameter_form_spec_aws_elbv2_application_target_errors():
    return Dictionary(
        title=Title("Upper levels for HTTP & Lambda user errors"),
        elements={
            "levels_http": DictElement(
                parameter_form=Dictionary(
                    title=Title("Upper levels for HTTP errors"),
                    elements=_fs_elements_http_errors(["2xx", "3xx", "4xx", "5xx"]),
                ),
            ),
            "levels_lambda": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper percentual levels for Lambda user errors"),
                    help_text=Help(
                        "Specify levels for Lambda user errors in percent "
                        "which refer to the total number of requests."
                    ),
                    elements=[
                        Percentage(title=Title("Warning at")),
                        Percentage(title=Title("Critical at")),
                    ],
                ),
            ),
        },
    )


rule_spec_aws_elbv2_target_errors = CheckParameters(
    name="aws_elbv2_target_errors",
    title=Title("AWS/ELBApplication Target Errors"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_elbv2_application_target_errors,
    condition=HostAndItemCondition(item_title=Title("Target group name")),
)

# .
#   .--EBS-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____| __ ) ___|                            |
#   |                         |  _| |  _ \___ \                            |
#   |                         | |___| |_) |__) |                           |
#   |                         |_____|____/____/                            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_form_spec_burst_balance() -> Dictionary:
    return Dictionary(elements=_fs_burst_balance())


rule_spec_aws_ebs_burst_balance = CheckParameters(
    name="aws_ebs_burst_balance",
    title=Title("AWS/EBS Burst Balance"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_burst_balance,
    condition=HostAndItemCondition(item_title=Title("Block storage name")),
)


def _parameter_form_spec_aws_ebs_limits() -> Dictionary:
    return Dictionary(
        elements={
            "block_store_snapshots": DictElement(
                parameter_form=fs_aws_limits(Title("Total Block store snapshots"), 100000),
            ),
            "block_store_space_standard": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Total Magnetic volumes space"), 300 * 1024**4, fs_limit_cls=DataSize
                ),
            ),
            "block_store_space_io1": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Total Provisioned IOPS SSD (io1) space"),
                    300 * 1024**4,
                    fs_limit_cls=DataSize,
                ),
            ),
            "block_store_iops_io1": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Total Provisioned IOPS SSD (io1) IO operations per seconds"), 300000
                ),
            ),
            "block_store_space_io2": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Total Provisioned IOPS SSD (io2) space"),
                    20 * 1024**4,
                    fs_limit_cls=DataSize,
                ),
            ),
            "block_store_iops_io2": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Total Provisioned IOPS SSD (io2) IO operations per seconds"), 100000
                ),
            ),
            "block_store_space_gp2": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Total General Purpose SSD (gp2) space"),
                    300 * 1024**4,
                    fs_limit_cls=DataSize,
                ),
            ),
            "block_store_space_gp3": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Total General Purpose SSD (gp3) space"),
                    300 * 1024**4,
                    fs_limit_cls=DataSize,
                ),
            ),
            "block_store_space_sc1": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Total Cold HDD space"), 300 * 1024**4, fs_limit_cls=DataSize
                ),
            ),
            "block_store_space_st1": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Total Throughput Optimized HDD space"),
                    300 * 1024**4,
                    fs_limit_cls=DataSize,
                ),
            ),
        }
    )


rule_spec_aws_ebs_limits = CheckParameters(
    name="aws_ebs_limits",
    title=Title("AWS/EBS Limits"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_ebs_limits,
    condition=HostAndItemCondition(
        item_title=Title("Region name"), item_form=_item_spec_aws_limits_generic()
    ),
)

# .
#   .--RDS-----------------------------------------------------------------.
#   |                          ____  ____  ____                            |
#   |                         |  _ \|  _ \/ ___|                           |
#   |                         | |_) | | | \___ \                           |
#   |                         |  _ <| |_| |___) |                          |
#   |                         |_| \_\____/|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _item_spec_aws_rds():
    return String(
        title=Title("Instance identifier & region"),
        help_text=Help(
            "Identfier of the DB instance and the name of the region in square brackets, e.g. "
            "'db-instance-1 \\[eu-central-1\\]'."
        ),
    )


rule_spec_aws_rds_cpu_credits = CheckParameters(
    name="aws_rds_cpu_credits",
    title=Title("AWS/RDS CPU Credits"),
    topic=Topic.APPLICATIONS,
    parameter_form=lambda: Dictionary(
        elements={**_fs_cpu_credits_balance(), **_fs_burst_balance()}
    ),
    condition=HostAndItemCondition(
        item_title=Title("Instance identifier & region"), item_form=_item_spec_aws_rds()
    ),
)


def _parameter_form_spec_aws_rds_disk_usage() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement(
                parameter_form=enable_deprecated_alternative(
                    wrapped_form_spec=CascadingSingleChoice(
                        title=Title("Upper levels for disk usage"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="alternative_levels",
                                title=Title("Set levels"),
                                parameter_form=TupleLevels(
                                    title=Title("Set levels"),
                                    elements=[
                                        Percentage(title=Title("Warning at")),
                                        Percentage(title=Title("Critical at")),
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="alternative_no_levels",
                                title=Title("No levels"),
                                parameter_form=TupleLevels(
                                    title=Title("No levels"),
                                    elements=[
                                        FixedValue(value=None),
                                        FixedValue(value=None),
                                    ],
                                ),
                            ),
                        ],
                    )
                ),
            )
        }
    )


rule_spec_aws_rds_disk_usage = CheckParameters(
    name="aws_rds_disk_usage",
    title=Title("AWS/RDS Disk Usage"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_rds_disk_usage,
    condition=HostAndItemCondition(
        item_title=Title("Instance identifier & region"), item_form=_item_spec_aws_rds()
    ),
)


def _parameter_form_spec_aws_rds_connections() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement(
                parameter_form=enable_deprecated_alternative(
                    wrapped_form_spec=CascadingSingleChoice(
                        title=Title("Upper levels for connections in use"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="alternative_levels",
                                title=Title("Set levels"),
                                parameter_form=TupleLevels(
                                    title=Title("Set levels"),
                                    elements=[
                                        Integer(title=Title("Warning at")),
                                        Integer(title=Title("Critical at")),
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="alternative_no_levels",
                                title=Title("No levels"),
                                parameter_form=TupleLevels(
                                    title=Title("No levels"),
                                    elements=[
                                        FixedValue(value=None),
                                        FixedValue(value=None),
                                    ],
                                ),
                            ),
                        ],
                    )
                ),
            )
        }
    )


rule_spec_aws_rds_connections = CheckParameters(
    name="aws_rds_connections",
    title=Title("AWS/RDS Connections"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_rds_connections,
    condition=HostAndItemCondition(
        item_title=Title("Instance identifier & region"), item_form=_item_spec_aws_rds()
    ),
)


def _parameter_form_spec_aws_rds_replica_lag():
    return Dictionary(
        elements={
            "lag_levels": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper levels on the replica lag"),
                    elements=[
                        Float(title=Title("Warning at"), unit_symbol="s"),
                        Float(title=Title("Critical at"), unit_symbol="s"),
                    ],
                ),
            ),
            "slot_levels": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper levels on the oldest replication slot lag"),
                    elements=[
                        DataSize(
                            title=Title("Warning at"),
                            displayed_magnitudes=(
                                IECMagnitude.BYTE,
                                IECMagnitude.KIBI,
                                IECMagnitude.MEBI,
                                IECMagnitude.GIBI,
                                IECMagnitude.TEBI,
                            ),
                        ),
                        DataSize(
                            title=Title("Critical at"),
                            displayed_magnitudes=(
                                IECMagnitude.BYTE,
                                IECMagnitude.KIBI,
                                IECMagnitude.MEBI,
                                IECMagnitude.GIBI,
                                IECMagnitude.TEBI,
                            ),
                        ),
                    ],
                ),
            ),
        }
    )


rule_spec_aws_rds_replica_lag = CheckParameters(
    name="aws_rds_replica_lag",
    title=Title("AWS/RDS Replica lag"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_rds_replica_lag,
    condition=HostAndItemCondition(
        item_title=Title("Instance identifier & region"), item_form=_item_spec_aws_rds()
    ),
)


def _parameter_form_spec_aws_rds_limits() -> Dictionary:
    return Dictionary(
        elements={
            "db_instances": DictElement(
                parameter_form=fs_aws_limits(Title("DB instances"), 40),
            ),
            "reserved_db_instances": DictElement(
                parameter_form=fs_aws_limits(Title("Reserved DB instances"), 40)
            ),
            "allocated_storage": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Allocated storage"), 100 * 1024**4, fs_limit_cls=DataSize
                ),
            ),
            "db_security_groups": DictElement(
                parameter_form=fs_aws_limits(Title("DB security groups"), 25)
            ),
            "auths_per_db_security_groups": DictElement(
                parameter_form=fs_aws_limits(Title("Authorizations per DB security group"), 20),
            ),
            "db_parameter_groups": DictElement(
                parameter_form=fs_aws_limits(Title("DB parameter groups"), 50)
            ),
            "manual_snapshots": DictElement(
                parameter_form=fs_aws_limits(Title("Manual snapshots"), 100),
            ),
            "event_subscriptions": DictElement(
                parameter_form=fs_aws_limits(Title("Event subscriptions"), 20)
            ),
            "db_subnet_groups": DictElement(
                parameter_form=fs_aws_limits(Title("DB subnet groups"), 50),
            ),
            "option_groups": DictElement(
                parameter_form=fs_aws_limits(Title("Option groups"), 20),
            ),
            "subnet_per_db_subnet_groups": DictElement(
                parameter_form=fs_aws_limits(Title("Subnet per DB subnet groups"), 20),
            ),
            "read_replica_per_master": DictElement(
                parameter_form=fs_aws_limits(Title("Read replica per master"), 5)
            ),
            "db_clusters": DictElement(
                parameter_form=fs_aws_limits(Title("DB clusters"), 40),
            ),
            "db_cluster_parameter_groups": DictElement(
                parameter_form=fs_aws_limits(Title("DB cluster parameter groups"), 50),
            ),
            "db_cluster_roles": DictElement(
                parameter_form=fs_aws_limits(Title("DB cluster roles"), 5),
            ),
        }
    )


rule_spec_aws_rds_limits = CheckParameters(
    name="aws_rds_limits",
    title=Title("AWS/RDS Limits"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_rds_limits,
    condition=HostAndItemCondition(
        item_title=Title("Region name"), item_form=_item_spec_aws_limits_generic()
    ),
)

# .
#   .--Cloudwatch----------------------------------------------------------.
#   |         ____ _                 _               _       _             |
#   |        / ___| | ___  _   _  __| |_      ____ _| |_ ___| |__          |
#   |       | |   | |/ _ \| | | |/ _` \ \ /\ / / _` | __/ __| '_ \         |
#   |       | |___| | (_) | |_| | (_| |\ V  V / (_| | || (__| | | |        |
#   |        \____|_|\___/ \__,_|\__,_| \_/\_/ \__,_|\__\___|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_form_spec_aws_cloudwatch_alarms_limits() -> Dictionary:
    return Dictionary(
        elements={
            "cloudwatch_alarms": DictElement(
                parameter_form=fs_aws_limits(Title("CloudWatch Alarms"), 5000)
            )
        }
    )


rule_spec_aws_cloudwatch_alarms_limits = CheckParameters(
    name="aws_cloudwatch_alarms_limits",
    title=Title("AWS/CloudWatch Alarms Limits"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_cloudwatch_alarms_limits,
    condition=HostAndItemCondition(
        item_title=Title("Region name"), item_form=_item_spec_aws_limits_generic()
    ),
)

# .
#   .--DynamoDB------------------------------------------------------------.
#   |         ____                                    ____  ____           |
#   |        |  _ \ _   _ _ __   __ _ _ __ ___   ___ |  _ \| __ )          |
#   |        | | | | | | | '_ \ / _` | '_ ` _ \ / _ \| | | |  _ \          |
#   |        | |_| | |_| | | | | (_| | | | | | | (_) | |_| | |_) |         |
#   |        |____/ \__, |_| |_|\__,_|_| |_| |_|\___/|____/|____/          |
#   |               |___/                                                  |
#   '----------------------------------------------------------------------'


def _fs_aws_dynamodb_capacity(title: Title, unit: str) -> Dictionary:
    elements_extr: list[FormSpec[Any]] = [
        Float(title=Title("Warning at"), unit_symbol=unit),
        Float(title=Title("Critical at"), unit_symbol=unit),
    ]

    # mypy is unhappy without splitting into elements_avg and elements_single_minmmax
    elements_avg: Mapping[str, DictElement] = {
        "levels_average": DictElement(
            parameter_form=Dictionary(
                title=Title("Levels on average usage"),
                elements={
                    "limit": DictElement(
                        parameter_form=Integer(
                            title=Title("Limit at (otherwise from AWS API for provisioned tables)"),
                            unit_symbol=unit,
                            prefill=DefaultValue(1),
                            help_text=Help(
                                "Specify the limit value against which the average consumption is "
                                "compared to compute the average usage. If not set, the limit "
                                "will be fetched from the AWS API. However, this is not possible "
                                "for on-demand tables. Therefore, no average usage can be "
                                "computed for these tables if this value is not specified."
                            ),
                            custom_validate=[
                                validators.NumberInRange(
                                    min_value=1, error_msg=Message("Integer field can not be empty")
                                )
                            ],
                        ),
                    ),
                    "levels_upper": DictElement(
                        parameter_form=TupleLevels(
                            title=Title("Upper levels in percentage of limit"),
                            elements=[
                                Percentage(title=Title("Warning at"), prefill=DefaultValue(80)),
                                Percentage(title=Title("Critical at"), prefill=DefaultValue(90)),
                            ],
                        ),
                    ),
                    "levels_lower": DictElement(
                        parameter_form=TupleLevels(
                            title=Title("Lower levels in percentage of limit"),
                            elements=[
                                Percentage(title=Title("Warning at")),
                                Percentage(title=Title("Critical at")),
                            ],
                        ),
                    ),
                },
            )
        )
    }

    elements_single_minmmax: Mapping[str, DictElement] = {
        "levels_%s" % extr: DictElement(
            parameter_form=Dictionary(
                title=Title("Levels on %s single-request consumption") % extr,
                elements={
                    "levels_upper": DictElement(
                        parameter_form=Tuple(title=Title("Upper levels"), elements=elements_extr),
                    ),
                    "levels_lower": DictElement(
                        parameter_form=Tuple(title=Title("Lower levels"), elements=elements_extr),
                    ),
                },
            ),
        )
        for extr in ["minimum", "maximum"]
    }

    return Dictionary(title=title, elements={**elements_avg, **elements_single_minmmax})


def _parameter_form_spec_aws_dynamodb_capacity() -> Dictionary:
    return Dictionary(
        title=Title("Levels on read/write capacity"),
        elements={
            "levels_read": DictElement(
                parameter_form=_fs_aws_dynamodb_capacity(Title("Levels on read capacity"), "RCU"),
            ),
            "levels_write": DictElement(
                parameter_form=_fs_aws_dynamodb_capacity(Title("Levels on write capacity"), "WCU"),
            ),
        },
    )


rule_spec_aws_dynamodb_capacity = CheckParameters(
    name="aws_dynamodb_capacity",
    title=Title("AWS/DynamoDB Read/Write Capacity"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_dynamodb_capacity,
    condition=HostCondition(),
)


def _parameter_form_spec_aws_dynamodb_latency() -> Dictionary:
    return Dictionary(
        title=Title("Levels on latency"),
        elements={
            f"levels_seconds_{operation.lower()}_{statistic}": DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper levels on %s latency of successful %s requests")
                    % (statistic, operation),
                    elements=[
                        Float(title=Title("Warning at"), unit_symbol="ms"),
                        Float(title=Title("Critical at"), unit_symbol="ms"),
                    ],
                ),
            )
            for operation in ["Query", "GetItem", "PutItem"]
            for statistic in ["average", "maximum"]
        },
    )


rule_spec_aws_dynamodb_latency = CheckParameters(
    name="aws_dynamodb_latency",
    title=Title("AWS/DynamoDB Latency"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_dynamodb_latency,
    condition=HostCondition(),
)

# .
#   .--WAFV2---------------------------------------------------------------.
#   |                __        ___    _______     ______                   |
#   |                \ \      / / \  |  ___\ \   / /___ \                  |
#   |                 \ \ /\ / / _ \ | |_   \ \ / /  __) |                 |
#   |                  \ V  V / ___ \|  _|   \ V /  / __/                  |
#   |                   \_/\_/_/   \_\_|      \_/  |_____|                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _item_spec_aws_wafv2_limits():
    return String(
        title=Title("Region name"),
        help_text=Help(
            "An AWS region name such as 'eu-central-1' or 'CloudFront' for WAFs in "
            "front of CloudFront resources"
        ),
    )


def _parameter_form_spec_aws_wafv2_limits() -> Dictionary:
    return Dictionary(
        title=Title("Limits and levels"),
        elements={
            "web_acls": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Web ACLs"), 100, title_default=Title("Default limit set by AWS")
                ),
            ),
            "rule_groups": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Rule groups"), 100, title_default=Title("Default limit set by AWS")
                ),
            ),
            "ip_sets": DictElement(
                parameter_form=fs_aws_limits(
                    Title("IP sets"), 100, title_default=Title("Default limit set by AWS")
                ),
            ),
            "regex_pattern_sets": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Regex sets"), 10, title_default=Title("Default limit set by AWS")
                ),
            ),
            "web_acl_capacity_units": DictElement(
                parameter_form=fs_aws_limits(
                    Title("Web ACL capacity units (WCUs)"),
                    1500,
                    title_default=Title("Default limit set by AWS"),
                ),
            ),
        },
    )


rule_spec_aws_wafv2_limits = CheckParameters(
    name="aws_wafv2_limits",
    title=Title("AWS/WAFV2 Limits"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_wafv2_limits,
    condition=HostAndItemCondition(
        item_title=Title("Region name"), item_form=_item_spec_aws_wafv2_limits()
    ),
)


def _parameter_form_spec_aws_wafv2_web_acl() -> Dictionary:
    return Dictionary(
        title=Title("Levels on Web ACL requests"),
        elements={
            "%s_requests_perc" % action: DictElement(
                parameter_form=TupleLevels(
                    title=Title("Upper levels on percentage of %s requests") % action,
                    elements=[
                        Percentage(title=Title("Warning at")),
                        Percentage(title=Title("Critical at")),
                    ],
                ),
            )
            for action in ["allowed", "blocked"]
        },
    )


rule_spec_aws_wafv2_web_acl = CheckParameters(
    name="aws_wafv2_web_acl",
    title=Title("AWS/WAFV2 Web ACL Requests"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_aws_wafv2_web_acl,
    condition=HostCondition(),
)
