#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, Iterable, List, Optional
from typing import Tuple as TupleType
from typing import Type

from cmk.utils.aws_constants import (
    AWSEC2InstFamilies,
    AWSEC2InstTypes,
    AWSEC2LimitsDefault,
    AWSEC2LimitsSpecial,
)

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    Dictionary,
    DictionaryEntry,
    Filesize,
    FixedValue,
    Float,
    Integer,
    ListOf,
    Percentage,
    TextInput,
    Transform,
    Tuple,
    ValueSpec,
)


def _vs_s3_buckets():
    return (
        "bucket_size_levels",
        Alternative(
            title=_("Upper levels for the bucket size"),
            elements=[
                Tuple(
                    title=_("Set levels"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
                Tuple(
                    title=_("No levels"),
                    elements=[
                        FixedValue(value=None, totext=""),
                        FixedValue(value=None, totext=""),
                    ],
                ),
            ],
        ),
    )


def _vs_glacier_vaults():
    return (
        "vault_size_levels",
        Alternative(
            title=_("Upper levels for the vault size"),
            elements=[
                Tuple(
                    title=_("Set levels"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
                Tuple(
                    title=_("No levels"),
                    elements=[
                        FixedValue(value=None, totext=""),
                        FixedValue(value=None, totext=""),
                    ],
                ),
            ],
        ),
    )


def _vs_burst_balance():
    return (
        "burst_balance_levels_lower",
        Alternative(
            title=_("Lower levels for burst balance"),
            elements=[
                Tuple(
                    title=_("Set levels"),
                    elements=[
                        Percentage(title=_("Warning at or below")),
                        Percentage(title=_("Critical at or below")),
                    ],
                ),
                Tuple(
                    title=_("No levels"),
                    elements=[
                        FixedValue(value=None, totext=""),
                        FixedValue(value=None, totext=""),
                    ],
                ),
            ],
        ),
    )


def _vs_cpu_credits_balance():
    return (
        "balance_levels_lower",
        Alternative(
            title=_("Lower levels for CPU balance"),
            elements=[
                Tuple(
                    title=_("Set levels"),
                    elements=[
                        Integer(title=_("Warning at or below")),
                        Integer(title=_("Critical at or below")),
                    ],
                ),
                Tuple(
                    title=_("No levels"),
                    elements=[
                        FixedValue(value=None, totext=""),
                        FixedValue(value=None, totext=""),
                    ],
                ),
            ],
        ),
    )


def _vs_elements_http_errors(
    http_err_codes: Iterable[str],
    title_add: Callable[[str], str] = lambda http_err_code: "",
) -> Iterable[TupleType[str, Tuple]]:
    return [
        (
            "levels_http_%s_perc" % http_err_code,
            Tuple(
                title=_("Upper percentual levels for HTTP %s errors") % http_err_code.upper()
                + title_add(http_err_code),
                help=_(
                    "Specify levels for HTTP %s errors in percent "
                    "which refer to the total number of requests."
                )
                % http_err_code.upper(),
                elements=[
                    Percentage(title=_("Warning at")),
                    Percentage(title=_("Critical at")),
                ],
            ),
        )
        for http_err_code in http_err_codes
    ]


def _vs_latency():
    return (
        "levels_latency",
        Tuple(
            title=_("Upper levels for latency"),
            elements=[
                Age(title=_("Warning at")),
                Age(title=_("Critical at")),
            ],
        ),
    )


def _item_spec_aws_limits_generic():
    return TextInput(title=_("Region name"), help=_("An AWS region name such as 'eu-central-1'"))


def _vs_limits(
    resource: str,
    default_limit: int,
    vs_limit_cls: Optional[Type[Filesize]] = None,
    unit: str = "",
    title_default: str = _("Limit from AWS API"),
) -> Alternative:

    if vs_limit_cls is None:
        vs_limit = Integer(
            title=resource,
            unit=unit,
            minvalue=1,
            default_value=default_limit,
        )
    else:
        vs_limit = vs_limit_cls(
            title=resource,
            minvalue=1,
            default_value=default_limit,
        )

    if resource:
        title: Optional[str] = _("Set limit and levels for %s") % resource
    else:
        title = None

    return Alternative(
        title=title,
        elements=[
            Tuple(
                title=_("Set levels"),
                elements=[
                    Alternative(
                        orientation="horizontal",
                        elements=[
                            FixedValue(
                                value=None,
                                title=title_default,
                                totext="",
                            ),
                            vs_limit,
                        ],
                    ),
                    Percentage(title=_("Warning at"), default_value=80.0),
                    Percentage(title=_("Critical at"), default_value=90.0),
                ],
            ),
            Tuple(
                title=_("No levels"),
                elements=[
                    FixedValue(value=None, totext=""),
                    FixedValue(value=None, totext=""),
                    FixedValue(value=None, totext=""),
                ],
            ),
        ],
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


def _item_spec_aws_glacier_vault_archives():
    return TextInput(title=_("The vault name"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_glacier_vault_archives",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_glacier_vault_archives,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(elements=[_vs_glacier_vaults()]),
        title=lambda: _("AWS/Glacier Vault Objects"),
    )
)


def _parameter_valuespec_aws_glacier_vaults():
    return Dictionary(elements=[_vs_glacier_vaults()])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_glacier_vaults",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_glacier_vaults,
        title=lambda: _("AWS/Glacier Vaults"),
    )
)


def _parameter_valuespec_aws_glacier_limits() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "number_of_vaults",
                _vs_limits(_("Vaults"), 1000),
            )
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_glacier_limits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_glacier_limits,
        title=lambda: _("AWS/Glacier Limits"),
    )
)

# .
#   .--S3------------------------------------------------------------------.
#   |                             ____ _____                               |
#   |                            / ___|___ /                               |
#   |                            \___ \ |_ \                               |
#   |                             ___) |__) |                              |
#   |                            |____/____/                               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _item_spec_aws_s3_buckets():
    return TextInput(title=_("Bucket name"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_s3_buckets_objects",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_s3_buckets,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(elements=[_vs_s3_buckets()]),
        title=lambda: _("AWS/S3 Bucket Objects"),
    )
)


def _parameter_valuespec_aws_s3_buckets():
    return Dictionary(elements=[_vs_s3_buckets()])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_s3_buckets",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_s3_buckets,
        title=lambda: _("AWS/S3 Buckets"),
    )
)


def _parameter_valuespec_aws_s3_requests():
    return Dictionary(
        elements=[
            (
                "get_requests_perc",
                Alternative(
                    title=_("Upper percentual levels for GET requests"),
                    elements=[
                        Tuple(
                            title=_("Set levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("No levels"),
                            elements=[
                                FixedValue(value=None, totext=""),
                                FixedValue(value=None, totext=""),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "put_requests_perc",
                Alternative(
                    title=_("Upper percentual levels for PUT requests"),
                    elements=[
                        Tuple(
                            title=_("Set levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("No levels"),
                            elements=[
                                FixedValue(value=None, totext=""),
                                FixedValue(value=None, totext=""),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "delete_requests_perc",
                Alternative(
                    title=_("Upper percentual levels for DELETE requests"),
                    elements=[
                        Tuple(
                            title=_("Set levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("No levels"),
                            elements=[
                                FixedValue(value=None, totext=""),
                                FixedValue(value=None, totext=""),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "head_requests_perc",
                Alternative(
                    title=_("Upper percentual levels for HEAD requests"),
                    elements=[
                        Tuple(
                            title=_("Set levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("No levels"),
                            elements=[
                                FixedValue(value=None, totext=""),
                                FixedValue(value=None, totext=""),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "post_requests_perc",
                Alternative(
                    title=_("Upper percentual levels for POST requests"),
                    elements=[
                        Tuple(
                            title=_("Set levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("No levels"),
                            elements=[
                                FixedValue(value=None, totext=""),
                                FixedValue(value=None, totext=""),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "select_requests_perc",
                Alternative(
                    title=_("Upper percentual levels for SELECT requests"),
                    elements=[
                        Tuple(
                            title=_("Set levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("No levels"),
                            elements=[
                                FixedValue(value=None, totext=""),
                                FixedValue(value=None, totext=""),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "list_requests_perc",
                Alternative(
                    title=_("Upper percentual levels for LIST requests"),
                    elements=[
                        Tuple(
                            title=_("Set levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("No levels"),
                            elements=[
                                FixedValue(value=None, totext=""),
                                FixedValue(value=None, totext=""),
                            ],
                        ),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_s3_requests",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_s3_buckets,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_s3_requests,
        title=lambda: _("AWS/S3 Bucket Requests"),
    )
)


def _parameter_valuespec_aws_s3_latency():
    return Dictionary(
        title=_("Levels on latency"),
        elements=[
            (
                "levels_seconds",
                Tuple(
                    title=_("Upper levels on total request latency"),
                    elements=[
                        Float(title=_("Warning at"), unit="ms"),
                        Float(title=_("Critical at"), unit="ms"),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_s3_latency",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_s3_buckets,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_s3_latency,
        title=lambda: _("AWS/S3 Latency"),
    )
)


def _parameter_valuespec_aws_s3_limits() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "buckets",
                _vs_limits(_("Buckets"), 100, title_default=_("Default limit set by AWS")),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_s3_limits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_s3_limits,
        title=lambda: _("AWS/S3 Limits"),
    )
)


def _parameter_valuespec_aws_s3_http_erros():
    return Dictionary(
        title=_("Upper levels for HTTP errors"), elements=_vs_elements_http_errors(["4xx", "5xx"])
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_s3_http_errors",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_s3_buckets,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_s3_http_erros,
        title=lambda: _("AWS/S3 HTTP Errors"),
    )
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


def _parameter_valuespec_aws_ec2_cpu_credits():
    return Dictionary(elements=[_vs_cpu_credits_balance()])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_ec2_cpu_credits",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_ec2_cpu_credits,
        title=lambda: _("AWS/EC2 CPU Credits"),
    )
)


def _vs_limits_inst_types():
    return ListOf(
        valuespec=CascadingDropdown(
            orientation="horizontal",
            choices=[
                (
                    inst_type,
                    inst_type,
                    _vs_limits(
                        _("%s instances") % inst_type,
                        AWSEC2LimitsSpecial.get(inst_type, AWSEC2LimitsDefault)[0],
                    ),
                )
                for inst_type in AWSEC2InstTypes
            ],
        ),
        title=_("Set limits and levels for running on-demand instances"),
    )


def _vs_limits_vcpu_families():
    return ListOf(
        valuespec=CascadingDropdown(
            orientation="horizontal",
            choices=[
                (
                    "%s_vcpu" % inst_fam,
                    fam_name,
                    _vs_limits(
                        fam_name,
                        AWSEC2LimitsSpecial.get("%s_vcpu" % inst_fam, AWSEC2LimitsDefault)[0],
                    ),
                )
                for inst_fam, fam_name in AWSEC2InstFamilies.items()
            ],
        ),
        title=_("Set limits and levels for running on-demand vCPUs on instance Families"),
    )


def _parameter_valuespec_aws_ec2_limits() -> Dictionary:
    return Dictionary(
        elements=[
            ("vpc_elastic_ip_addresses", _vs_limits(_("VPC Elastic IP Addresses"), 5)),
            ("elastic_ip_addresses", _vs_limits(_("Elastic IP Addresses"), 5)),
            ("vpc_sec_group_rules", _vs_limits(_("Rules of VPC security group"), 120)),
            ("vpc_sec_groups", _vs_limits(_("VPC security groups"), 2500)),
            (
                "if_vpc_sec_group",
                _vs_limits(_("VPC security groups of elastic network interface"), 5),
            ),
            ("spot_inst_requests", _vs_limits(_("Spot Instance Requests"), 20)),
            ("active_spot_fleet_requests", _vs_limits(_("Active Spot Fleet Requests"), 1000)),
            (
                "spot_fleet_total_target_capacity",
                _vs_limits(_("Spot Fleet Requests Total Target Capacity"), 5000),
            ),
            (
                "running_ondemand_instances_total",
                _vs_limits(_("Total Running On-Demand Instances(Deprecated by AWS)"), 20),
            ),
            ("running_ondemand_instances_vcpus", _vs_limits_vcpu_families()),
            ("running_ondemand_instances", _vs_limits_inst_types()),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_ec2_limits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_ec2_limits,
        title=lambda: _("AWS/EC2 Limits"),
    )
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


def _item_spec_aws_costs_and_usage():
    return TextInput(title=_("The service name"))


def _parameter_valuespec_aws_costs_and_usage():
    return Dictionary(
        elements=[
            (
                "levels_unblended",
                Tuple(
                    title=_("Upper levels for unblended costs"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("USD per day")),
                        Integer(title=_("Critical at"), unit=_("USD per day")),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_costs_and_usage",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_costs_and_usage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_costs_and_usage,
        title=lambda: _("AWS/CE Costs and Usage"),
    )
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


def _parameter_valuespec_aws_elb_statistics():
    return Dictionary(
        elements=[
            (
                "levels_surge_queue_length",
                Tuple(
                    title=_("Upper levels for surge queue length"),
                    elements=[
                        Integer(title=_("Warning at"), default_value=1024),
                        Integer(title=_("Critical at"), default_value=1024),
                    ],
                ),
            ),
            (
                "levels_spillover",
                Tuple(
                    title=_(
                        "Upper levels for the number of requests that were rejected (spillover)"
                    ),
                    elements=[
                        Float(
                            title=_("Warning at"),
                            display_format="%.3f",
                            default_value=0.001,
                            unit="/s",
                        ),
                        Float(
                            title=_("Critical at"),
                            display_format="%.3f",
                            default_value=0.001,
                            unit="/s",
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_statistics",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_statistics,
        title=lambda: _("AWS/ELB Statistics"),
    )
)


def _parameter_valuespec_aws_elb_latency():
    return Dictionary(elements=[_vs_latency()])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_latency",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_latency,
        title=lambda: _("AWS/ELB Latency"),
    )
)


def _transform_aws_elb_http(p):

    if "levels_load_balancers" in p:
        return p
    p_trans = {"levels_load_balancers": p, "levels_backend_targets": {}}

    for http_err_code in ["4xx", "5xx"]:
        levels_key = "levels_http_%s_perc" % http_err_code
        if levels_key in p:
            p_trans["levels_backend_targets"][levels_key] = p[levels_key]

    return p_trans


def _parameter_valuespec_aws_elb_http():
    return Transform(
        Dictionary(
            title=_("Upper levels for HTTP errors"),
            elements=[
                (
                    "levels_load_balancers",
                    Dictionary(
                        title=_("Upper levels for Load Balancers"),
                        elements=_vs_elements_http_errors(
                            ["3xx", "4xx", "5xx", "500", "502", "503", "504"],
                            title_add=lambda http_err_code: ""
                            if http_err_code in ["4xx", "5xx"]
                            else " (Application Load Balancers only)",
                        ),
                    ),
                ),
                (
                    "levels_backend_targets",
                    Dictionary(
                        title=_("Upper levels for Backend"),
                        elements=_vs_elements_http_errors(["2xx", "3xx", "4xx", "5xx"]),
                    ),
                ),
            ],
        ),
        forth=_transform_aws_elb_http,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_http",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_http,
        title=lambda: _("AWS/ELB HTTP Errors"),
    )
)


def _parameter_valuespec_aws_elb_healthy_hosts():
    return Dictionary(
        elements=[
            (
                "levels_overall_hosts_health_perc",
                Tuple(
                    title=_("Upper percentual levels for healthy hosts"),
                    help=_(
                        "These levels refer to the total number of instances or hosts "
                        "that are registered to the load balancer which is the sum of "
                        "healthy and unhealthy instances."
                    ),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_healthy_hosts",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_healthy_hosts,
        title=lambda: _("AWS/ELB Healthy Hosts"),
    )
)


def _parameter_valuespec_aws_elb_backend_connection_errors():
    return Dictionary(
        elements=[
            (
                "levels_backend_connections_errors_rate",
                Tuple(
                    title=_("Upper levels for backend connection errors per second"),
                    elements=[
                        Float(title=_("Warning at"), unit="/s"),
                        Float(title=_("Critical at"), unit="/s"),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elb_backend_connection_errors",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_backend_connection_errors,
        title=lambda: _("AWS/ELB Backend Connection Errors"),
    )
)


def _parameter_valuespec_aws_elb_limits() -> Dictionary:
    return Dictionary(
        elements=[
            ("load_balancers", _vs_limits(_("Load balancers"), 20)),
            ("load_balancer_listeners", _vs_limits(_("Listeners per load balancer"), 100)),
            (
                "load_balancer_registered_instances",
                _vs_limits(_("Registered instances per load balancer"), 1000),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_elb_limits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elb_limits,
        title=lambda: _("AWS/ELB Limits"),
    )
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


def _parameter_valuespec_aws_elbv2_limits() -> Dictionary:
    return Dictionary(
        elements=[
            ("application_load_balancers", _vs_limits(_("Application Load balancers"), 20)),
            (
                "application_load_balancer_rules",
                _vs_limits(_("Application Load Balancer Rules"), 100),
            ),
            (
                "application_load_balancer_listeners",
                _vs_limits(_("Application Load Balancer Listeners"), 50),
            ),
            (
                "application_load_balancer_target_groups",
                _vs_limits(_("Application Load Balancer Target Groups"), 3000),
            ),
            (
                "application_load_balancer_certificates",
                _vs_limits(_("Application Load balancer Certificates"), 25),
            ),
            ("network_load_balancers", _vs_limits(_("Network Load balancers"), 20)),
            (
                "network_load_balancer_listeners",
                _vs_limits(_("Network Load Balancer Listeners"), 50),
            ),
            (
                "network_load_balancer_target_groups",
                _vs_limits(_("Network Load Balancer Target Groups"), 3000),
            ),
            ("load_balancer_target_groups", _vs_limits(_("Load balancers Target Groups"), 3000)),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_elbv2_limits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elbv2_limits,
        title=lambda: _("AWS/ELBv2 Limits"),
    )
)


def _parameter_valuespec_aws_elbv2_lcu():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper levels for load balancer capacity units"),
                    elements=[
                        Float(title=_("Warning at")),
                        Float(title=_("Critical at")),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_elbv2_lcu",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elbv2_lcu,
        title=lambda: _("AWS/ELBv2 LCU"),
    )
)


def _parameter_valuespec_aws_elbv2_application_target_errors():
    return Dictionary(
        title=_("Upper levels for HTTP & Lambda user errors"),
        elements=[
            (
                "levels_http",
                Dictionary(
                    title=_("Upper levels for HTTP errors"),
                    elements=_vs_elements_http_errors(["2xx", "3xx", "4xx", "5xx"]),
                ),
            ),
            (
                "levels_lambda",
                Tuple(
                    title=_("Upper percentual levels for Lambda user errors"),
                    help=_(
                        "Specify levels for Lambda user errors in percent "
                        "which refer to the total number of requests."
                    ),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


def _item_spec_aws_elbv2_target_errors():
    return TextInput(title=_("Target group name"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_elbv2_target_errors",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_elbv2_target_errors,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_elbv2_application_target_errors,
        title=lambda: _("AWS/ELBApplication Target Errors"),
    )
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


def _item_spec_aws_ebs_burst_balance():
    return TextInput(title=_("Block storage name"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_ebs_burst_balance",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_ebs_burst_balance,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(elements=[_vs_burst_balance()]),
        title=lambda: _("AWS/EBS Burst Balance"),
    )
)


def _parameter_valuespec_aws_ebs_limits() -> Dictionary:
    return Dictionary(
        elements=[
            ("block_store_snapshots", _vs_limits(_("Total Block store snapshots"), 100000)),
            (
                "block_store_space_standard",
                _vs_limits(
                    _("Total Magnetic volumes space"), 300 * 1024**4, vs_limit_cls=Filesize
                ),
            ),
            (
                "block_store_space_io1",
                _vs_limits(
                    _("Total Provisioned IOPS SSD space"), 300 * 1024**4, vs_limit_cls=Filesize
                ),
            ),
            (
                "block_store_iops_io1",
                _vs_limits(_("Total Provisioned IOPS SSD IO operations per seconds"), 300000),
            ),
            (
                "block_store_space_gp2",
                _vs_limits(
                    _("Total General Purpose SSD space"), 300 * 1024**4, vs_limit_cls=Filesize
                ),
            ),
            (
                "block_store_space_sc1",
                _vs_limits(_("Total Cold HDD space"), 300 * 1024**4, vs_limit_cls=Filesize),
            ),
            (
                "block_store_space_st1",
                _vs_limits(
                    _("Total Throughput Optimized HDD space"),
                    300 * 1024**4,
                    vs_limit_cls=Filesize,
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_ebs_limits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_ebs_limits,
        title=lambda: _("AWS/EBS Limits"),
    )
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
    return TextInput(
        title=_("Instance identifier & region"),
        help="Identfier of the DB instance and the name of the region in square brackets, e.g. "
        "'db-instance-1 \\[eu-central-1\\]'.",
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_rds_cpu_credits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_rds,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(
            elements=[_vs_cpu_credits_balance(), _vs_burst_balance()]
        ),
        title=lambda: _("AWS/RDS CPU Credits"),
    )
)


def _parameter_valuespec_aws_rds_disk_usage():
    return Dictionary(
        elements=[
            (
                "levels",
                Alternative(
                    title=_("Upper levels for disk usage"),
                    elements=[
                        Tuple(
                            title=_("Set levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("No levels"),
                            elements=[
                                FixedValue(value=None, totext=""),
                                FixedValue(value=None, totext=""),
                            ],
                        ),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_rds_disk_usage",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_rds,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_rds_disk_usage,
        title=lambda: _("AWS/RDS Disk Usage"),
    )
)


def _parameter_valuespec_aws_rds_connections():
    return Dictionary(
        elements=[
            (
                "levels",
                Alternative(
                    title=_("Upper levels for connections in use"),
                    elements=[
                        Tuple(
                            title=_("Set levels"),
                            elements=[
                                Integer(title=_("Warning at")),
                                Integer(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("No levels"),
                            elements=[
                                FixedValue(value=None, totext=""),
                                FixedValue(value=None, totext=""),
                            ],
                        ),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_rds_connections",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_rds,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_rds_connections,
        title=lambda: _("AWS/RDS Connections"),
    )
)


def _parameter_valuespec_aws_rds_replica_lag():
    return Dictionary(
        elements=[
            (
                "lag_levels",
                Tuple(
                    title=_("Upper levels on the replica lag"),
                    elements=[
                        Float(title=_("Warning at"), unit="s", display_format="%.3f"),
                        Float(title=_("Critical at"), unit="s", display_format="%.3f"),
                    ],
                ),
            ),
            (
                "slot_levels",
                Tuple(
                    title=_("Upper levels on the oldest replication slot lag"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_rds_replica_lag",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_rds,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_rds_replica_lag,
        title=lambda: _("AWS/RDS Replica lag"),
    )
)


def _parameter_valuespec_aws_rds_limits() -> Dictionary:
    return Dictionary(
        elements=[
            ("db_instances", _vs_limits(_("DB instances"), 40)),
            ("reserved_db_instances", _vs_limits(_("Reserved DB instances"), 40)),
            (
                "allocated_storage",
                _vs_limits(_("Allocated storage"), 100 * 1024**4, vs_limit_cls=Filesize),
            ),
            ("db_security_groups", _vs_limits(_("DB security groups"), 25)),
            (
                "auths_per_db_security_groups",
                _vs_limits(_("Authorizations per DB security group"), 20),
            ),
            ("db_parameter_groups", _vs_limits(_("DB parameter groups"), 50)),
            ("manual_snapshots", _vs_limits(_("Manual snapshots"), 100)),
            ("event_subscriptions", _vs_limits(_("Event subscriptions"), 20)),
            ("db_subnet_groups", _vs_limits(_("DB subnet groups"), 50)),
            ("option_groups", _vs_limits(_("Option groups"), 20)),
            ("subnet_per_db_subnet_groups", _vs_limits(_("Subnet per DB subnet groups"), 20)),
            ("read_replica_per_master", _vs_limits(_("Read replica per master"), 5)),
            ("db_clusters", _vs_limits(_("DB clusters"), 40)),
            ("db_cluster_parameter_groups", _vs_limits(_("DB cluster parameter groups"), 50)),
            ("db_cluster_roles", _vs_limits(_("DB cluster roles"), 5)),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_rds_limits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_rds_limits,
        title=lambda: _("AWS/RDS Limits"),
    )
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


def _parameter_valuespec_aws_cloudwatch_alarms_limits() -> Dictionary:
    return Dictionary(
        elements=[
            ("cloudwatch_alarms", _vs_limits(_("CloudWatch Alarms"), 5000)),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_cloudwatch_alarms_limits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_cloudwatch_alarms_limits,
        title=lambda: _("AWS/CloudWatch Alarms Limits"),
    )
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


def _parameter_valuespec_aws_dynamodb_limits() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "number_of_tables",
                _vs_limits(
                    _("Number of tables"),
                    256,
                    unit="tables",
                    title_default="Default limit set by AWS",
                ),
            ),
            (
                "read_capacity",
                _vs_limits(_("Read capacity"), 80000, unit="RCU"),
            ),
            (
                "write_capacity",
                _vs_limits(_("Write capacity"), 80000, unit="WCU"),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_dynamodb_limits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_dynamodb_limits,
        title=lambda: _("AWS/DynamoDB Limits"),
    )
)


def _vs_aws_dynamodb_capacity(title: str, unit: str) -> Dictionary:

    elements_extr: List[ValueSpec] = [
        Float(title=_("Warning at"), unit=unit),
        Float(title=_("Critical at"), unit=unit),
    ]

    # mypy is unhappy without splitting into elements_avg and elements_single_minmmax
    elements_avg: List[DictionaryEntry] = [
        (
            "levels_average",
            Dictionary(
                title=_("Levels on average usage"),
                elements=[
                    (
                        "limit",
                        Integer(
                            title=_("Limit at (otherwise from AWS API for provisioned tables)"),
                            unit=unit,
                            minvalue=1,
                            default_value=1,
                            help=_(
                                "Specify the limit value against which the average consumption is "
                                "compared to compute the average usage. If not set, the limit "
                                "will be fetched from the AWS API. However, this is not possible "
                                "for on-demand tables. Therefore, no average usage can be "
                                "computed for these tables if this value is not specified."
                            ),
                        ),
                    ),
                    (
                        "levels_upper",
                        Tuple(
                            title=_("Upper levels in percentage of limit"),
                            elements=[
                                Percentage(title=_("Warning at"), default_value=80),
                                Percentage(title=_("Critical at"), default_value=90),
                            ],
                        ),
                    ),
                    (
                        "levels_lower",
                        Tuple(
                            title=_("Lower levels in percentage of limit"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                    ),
                ],
            ),
        ),
    ]

    elements_single_minmmax: List[DictionaryEntry] = [
        (
            "levels_%s" % extr,
            Dictionary(
                title=_("Levels on %s single-request consumption") % extr,
                elements=[
                    ("levels_upper", Tuple(title=_("Upper levels"), elements=elements_extr)),
                    ("levels_lower", Tuple(title=_("Lower levels"), elements=elements_extr)),
                ],
            ),
        )
        for extr in ["minimum", "maximum"]
    ]

    return Dictionary(title=title, elements=elements_avg + elements_single_minmmax)


def _parameter_valuespec_aws_dynamodb_capacity() -> Dictionary:
    return Dictionary(
        title=_("Levels on Read/Write Capacity"),
        elements=[
            (
                "levels_read",
                _vs_aws_dynamodb_capacity(_("Levels on read capacity"), "RCU"),
            ),
            (
                "levels_write",
                _vs_aws_dynamodb_capacity(_("Levels on write capacity"), "WCU"),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_dynamodb_capacity",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_dynamodb_capacity,
        title=lambda: _("AWS/DynamoDB Read/Write Capacity"),
    )
)


def _parameter_valuespec_aws_dynamodb_latency() -> Dictionary:
    return Dictionary(
        title=_("Levels on latency"),
        elements=[
            (
                "levels_seconds_%s_%s" % (operation.lower(), statistic),
                Tuple(
                    title=_("Upper levels on %s latency of successful %s requests")
                    % (statistic, operation),
                    elements=[
                        Float(title=_("Warning at"), unit="ms"),
                        Float(title=_("Critical at"), unit="ms"),
                    ],
                ),
            )
            for operation in ["Query", "GetItem", "PutItem"]
            for statistic in ["average", "maximum"]
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_dynamodb_latency",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_dynamodb_latency,
        title=lambda: _("AWS/DynamoDB Latency"),
    )
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
    return TextInput(
        title=_("Region name"),
        help=_(
            "An AWS region name such as 'eu-central-1' or 'CloudFront' for WAFs in "
            "front of CloudFront resources"
        ),
    )


def _parameter_valuespec_aws_wafv2_limits() -> Dictionary:
    return Dictionary(
        title=_("Limits and levels"),
        elements=[
            (
                "web_acls",
                _vs_limits(_("Web ACLs"), 100, title_default="Default limit set by AWS"),
            ),
            (
                "rule_groups",
                _vs_limits(_("Rule groups"), 100, title_default="Default limit set by AWS"),
            ),
            (
                "ip_sets",
                _vs_limits(_("IP sets"), 100, title_default="Default limit set by AWS"),
            ),
            (
                "regex_pattern_sets",
                _vs_limits(_("Regex sets"), 10, title_default="Default limit set by AWS"),
            ),
            (
                "web_acl_capacity_units",
                _vs_limits(
                    _("Web ACL capacity units (WCUs)"),
                    1500,
                    title_default="Default limit set by AWS",
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_wafv2_limits",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_wafv2_limits,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_wafv2_limits,
        title=lambda: _("AWS/WAFV2 Limits"),
    )
)


def _parameter_valuespec_aws_wafv2_web_acl() -> Dictionary:
    return Dictionary(
        title=_("Levels on Web ACL requests"),
        elements=[
            (
                "%s_requests_perc" % action,
                Tuple(
                    title=_("Upper levels on percentage of %s requests") % action,
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            )
            for action in ["allowed", "blocked"]
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="aws_wafv2_web_acl",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_wafv2_web_acl,
        title=lambda: _("AWS/WAFV2 Web ACL Requests"),
    )
)

# .
#   .--Lambda--------------------------------------------------------------.
#   |               _                    _         _                       |
#   |              | |    __ _ _ __ ___ | |__   __| | __ _                 |
#   |              | |   / _` | '_ ` _ \| '_ \ / _` |/ _` |                |
#   |              | |__| (_| | | | | | | |_) | (_| | (_| |                |
#   |              |_____\__,_|_| |_| |_|_.__/ \__,_|\__,_|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _parameter_valuespec_aws_lambda_performance():
    return Dictionary(
        elements=[
            (
                "levels_duration_percent",
                Tuple(
                    title=_("Upper levels for duration in percent of the timeout"),
                    elements=[
                        Percentage(title=_("Warning at"), display_format="%.2f", default_value=0.9),
                        Percentage(
                            title=_("Critical at"), display_format="%.2f", default_value=0.95
                        ),
                    ],
                    help=_(
                        'Specify the upper levels for the elapsed time of a function’s execution (duration) in percent of the AWS Lambda configuration value "Timeout".'
                    ),
                ),
            ),
            (
                "levels_duration_absolute",
                Tuple(
                    title=_("Upper levels for duration in seconds"),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                    help=_(
                        "Specify the upper levels for the elapsed time of a function’s execution (duration)."
                    ),
                ),
            ),
            (
                "levels_errors",
                Tuple(
                    title=_("Upper levels for errors"),
                    elements=[
                        Float(
                            title=_("Warning at"),
                            size=6,
                            display_format="%.5f",
                            default_value=0.00028,
                            unit="1/s",
                        ),
                        Float(
                            title=_("Critical at"),
                            size=6,
                            display_format="%.5f",
                            default_value=0.00028,
                            unit="1/s",
                        ),
                    ],
                    help=_(
                        "Specify the upper levels for the number of failed invocations per second due to function errors. Default is CRIT for more than one error per hour (ca. 1.0/3600)."
                    ),
                ),
            ),
            (
                "levels_invocations",
                Tuple(
                    title=_("Upper levels for invocations"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                    help=_("Specify the upper levels for the number of invocations per second."),
                ),
            ),
            (
                "levels_throttles",
                Tuple(
                    title=_("Upper levels for throttles"),
                    elements=[
                        Float(
                            title=_("Warning at"),
                            size=6,
                            display_format="%.5f",
                            default_value=0.00028,
                            unit="1/s",
                        ),
                        Float(
                            title=_("Critical at"),
                            size=6,
                            display_format="%.5f",
                            default_value=0.00028,
                            unit="1/s",
                        ),
                    ],
                    help=_(
                        "Specify the upper levels for the number of invocations per second that exceeded the concurrent limits (throttles). Default is CRIT for more than one error per hour (ca. 1.0/3600)."
                    ),
                ),
            ),
            (
                "levels_iterator_age",
                Tuple(
                    title=_("Upper levels for iterator age"),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                    help=_(
                        "Specify the upper levels in seconds for the age of the last record for each batch of records processed (iterator age). "
                        "A high iterator age could result from the following scenarios: a high execution duration for a function, not enough shards in a stream, invocation errors, insufficient batch size. "
                        "This metric is only reported for stream-based invocations."
                    ),
                ),
            ),
            (
                "levels_dead_letter_errors",
                Tuple(
                    title=_("Upper levels for dead letter errors"),
                    elements=[
                        Float(
                            title=_("Warning at"),
                            size=6,
                            display_format="%.5f",
                            default_value=0.00028,
                            unit="1/s",
                        ),
                        Float(
                            title=_("Critical at"),
                            size=6,
                            display_format="%.5f",
                            default_value=0.00028,
                            unit="1/s",
                        ),
                    ],
                    help=_(
                        "Specify the upper levels for the number of discarded events per second that could not be processed. "
                        "This metric is only reported for asynchronous invocations. Default is CRIT for more than one error per hour (ca. 1.0/3600)."
                    ),
                ),
            ),
            (
                "levels_init_duration_absolute",
                Tuple(
                    title=_("Init duration with absolute limits"),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                ),
            ),
            (
                "levels_cold_starts_in_percent",
                Tuple(
                    title=_("Cold starts in percent"),
                    elements=[
                        Percentage(
                            title=_("Warning at"), display_format="%.2f", default_value=10.0
                        ),
                        Percentage(
                            title=_("Critical at"), display_format="%.2f", default_value=20.0
                        ),
                    ],
                    help=_(
                        "Specify the upper levels for the cold starts in percent of total invocations."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_lambda_performance",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_lambda_performance,
        title=lambda: _("AWS/Lambda Performance"),
    )
)


def _parameter_valuespec_aws_lambda_concurrency():
    return Dictionary(
        elements=[
            (
                "levels_concurrent_executions_in_percent",
                Tuple(
                    title=_(
                        "Upper levels for concurrent executions in percent of the region limit"
                    ),
                    elements=[
                        Percentage(title=_("Warning at"), display_format="%.2f", default_value=0.9),
                        Percentage(
                            title=_("Critical at"), display_format="%.2f", default_value=0.95
                        ),
                    ],
                ),
            ),
            (
                "levels_unreserved_concurrent_executions_in_percent",
                Tuple(
                    title=_(
                        "Upper levels for unreserved concurrent executions in percent of the region limit"
                    ),
                    elements=[
                        Percentage(title=_("Warning at"), display_format="%.2f", default_value=0.9),
                        Percentage(
                            title=_("Critical at"), display_format="%.2f", default_value=0.95
                        ),
                    ],
                ),
            ),
            (
                "levels_concurrent_executions_absolute",
                Tuple(
                    title=_("Upper levels for concurrent executions"),
                    elements=[
                        Float(title=_("Warning at"), display_format="%.1f", unit="1/s"),
                        Float(title=_("Critical at"), display_format="%.1f", unit="1/s"),
                    ],
                ),
            ),
            (
                "levels_unreserved_concurrent_executions_absolute",
                Tuple(
                    title=_("Upper levels for unreserved concurrent executions"),
                    elements=[
                        Float(title=_("Warning at"), display_format="%.1f", unit="1/s"),
                        Float(title=_("Critical at"), display_format="%.1f", unit="1/s"),
                    ],
                ),
            ),
            (
                "levels_provisioned_concurrency_executions",
                Tuple(
                    title=_("Upper levels for provisioned concurrent executions per second"),
                    elements=[
                        Float(title=_("Warning at"), size=6, display_format="%.5f", unit="1/s"),
                        Float(title=_("Critical at"), size=6, display_format="%.5f", unit="1/s"),
                    ],
                ),
            ),
            (
                "levels_provisioned_concurrency_invocations",
                Tuple(
                    title=_("Upper levels for provisioned concurrent invocations per second"),
                    elements=[
                        Float(title=_("Warning at"), size=6, display_format="%.5f", unit="1/s"),
                        Float(title=_("Critical at"), size=6, display_format="%.5f", unit="1/s"),
                    ],
                ),
            ),
            (
                "levels_provisioned_concurrency_spillover_invocations",
                Tuple(
                    title=_(
                        "Upper levels for provisioned concurrency spillover invocations per second"
                    ),
                    elements=[
                        Float(
                            title=_("Warning at"),
                            size=6,
                            display_format="%.5f",
                            default_value=0.00028,
                            unit="1/s",
                        ),
                        Float(
                            title=_("Critical at"),
                            size=6,
                            display_format="%.5f",
                            default_value=0.00028,
                            unit="1/s",
                        ),
                    ],
                    help=_(
                        "Specify the upper levels for the number of invocations per second that are run on non-provisioned concurrency"
                        " (spillover invocations) when all provisioned concurrency is in use."
                        " Default is CRIT for more than one spillover invocation per hour (ca. 1.0/3600)."
                    ),
                ),
            ),
            (
                "levels_provisioned_concurrency_utilization",
                Tuple(
                    title=_("Upper levels provisioned concurrency utilization"),
                    elements=[
                        Percentage(title=_("Warning at"), display_format="%.2f", default_value=0.9),
                        Percentage(
                            title=_("Critical at"), display_format="%.2f", default_value=0.95
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_lambda_concurrency",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_lambda_concurrency,
        title=lambda: _("AWS/Lambda Concurrency"),
    )
)


def _parameter_valuespec_aws_lambda_memory() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "levels_code_size_in_percent",
                Tuple(
                    title=_("Upper levels for code size in percent of the region limit"),
                    elements=[
                        Percentage(title=_("Warning at"), display_format="%.2f", default_value=0.9),
                        Percentage(
                            title=_("Critical at"), display_format="%.2f", default_value=0.95
                        ),
                    ],
                ),
            ),
            (
                "levels_code_size_absolute",
                Tuple(
                    title=_("Upper levels for code size"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "levels_memory_used_in_percent",
                Tuple(
                    title=_("Upper levels for memory used in percent of the Lambda function limit"),
                    elements=[
                        Percentage(title=_("Warning at"), display_format="%.2f", default_value=0.9),
                        Percentage(
                            title=_("Critical at"), display_format="%.2f", default_value=0.95
                        ),
                    ],
                ),
            ),
            (
                "levels_memory_size_absolute",
                Tuple(
                    title=_("Upper levels for memory used"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_lambda_memory",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_lambda_memory,
        title=lambda: _("AWS/Lambda Memory"),
    )
)


def _parameter_valuespec_aws_route53() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "levels_connection_time",
                Tuple(
                    title=_("Upper levels for connection_time"),
                    elements=[
                        Float(title=_("Warning at"), unit="s", default_value=0.2),
                        Float(title=_("Critical at"), unit="s", default_value=0.5),
                    ],
                ),
            ),
            (
                "levels_health_check_percentage_healthy",
                Tuple(
                    title=_("Lower levels for health check percentage healty"),
                    elements=[
                        Percentage(
                            title=_("Warning at"), display_format="%.2f", default_value=100.0
                        ),
                        Percentage(
                            title=_("Critical at"), display_format="%.2f", default_value=100.0
                        ),
                    ],
                ),
            ),
            (
                "levels_ssl_handshake_time",
                Tuple(
                    title=_("Upper levels for SSL handshake time"),
                    elements=[
                        Float(title=_("Warning at"), unit="s", default_value=0.4),
                        Float(title=_("Critical at"), unit="s", default_value=1.0),
                    ],
                ),
            ),
            (
                "levels_time_to_first_byte",
                Tuple(
                    title=_("Upper levels for time to first byte"),
                    elements=[
                        Float(title=_("Warning at"), unit="s", default_value=0.4),
                        Float(title=_("Critical at"), unit="s", default_value=1.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="aws_route53",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_aws_limits_generic,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_aws_route53,
        title=lambda: _("AWS/Route53"),
    )
)
