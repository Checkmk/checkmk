#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import IgnoreResultsError, register
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.aws import discover_aws_generic, extract_aws_metrics_by_labels, parse_aws
from .utils.interfaces import CHECK_DEFAULT_PARAMETERS, check_single_interface, Interface

Section = Mapping[str, float]

EC2DefaultItemName = "Summary"


def parse_aws_ec2(string_table: StringTable) -> Section:
    """
    >>> parse_aws_ec2([[
    ... '[{"Id":', '"id_10_CPUCreditUsage",', '"Label":', '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",',
    ... '"Timestamps":', '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0030055,', 'null]],',
    ... '"StatusCode":', '"Complete"}]']])
    {'CPUCreditUsage': 0.0030055}
    """
    metrics = extract_aws_metrics_by_labels(
        [
            "CPUCreditUsage",
            "CPUCreditBalance",
            "CPUUtilization",
            "DiskReadOps",
            "DiskWriteOps",
            "DiskReadBytes",
            "DiskWriteBytes",
            "NetworkIn",
            "NetworkOut",
            "StatusCheckFailed_Instance",
            "StatusCheckFailed_System",
        ],
        parse_aws(string_table),
    )
    # We get exactly one entry: {INST-ID: METRICS}
    # INST-ID is the piggyback host name
    try:
        inst_metrics = list(metrics.values())[-1]
    except IndexError:
        inst_metrics = {}
    return inst_metrics


register.agent_section(
    name="aws_ec2",
    parse_function=parse_aws_ec2,
)

# .
#   .--network IO----------------------------------------------------------.
#   |                     _                      _      ___ ___            |
#   |          _ __   ___| |___      _____  _ __| | __ |_ _/ _ \           |
#   |         | '_ \ / _ \ __\ \ /\ / / _ \| '__| |/ /  | | | | |          |
#   |         | | | |  __/ |_ \ V  V / (_) | |  |   <   | | |_| |          |
#   |         |_| |_|\___|\__| \_/\_/ \___/|_|  |_|\_\ |___\___/           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_aws_ec2_network_io(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic(
        {EC2DefaultItemName: section},
        ["NetworkIn", "NetworkOut"],
    )


def check_aws_ec2_network_io(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    try:
        interface = Interface(
            index="0",
            descr=item,
            alias=item,
            type="1",
            oper_status="1",
            in_octets=section["NetworkIn"] / 60,
            out_octets=section["NetworkOut"] / 60,
        )
    except KeyError:
        raise IgnoreResultsError("Currently no data from AWS")
    yield from check_single_interface(item, params, interface, input_is_rate=True)


register.check_plugin(
    name="aws_ec2_network_io",
    sections=["aws_ec2"],
    service_name="AWS/EC2 Network IO %s",
    discovery_function=discover_aws_ec2_network_io,
    check_ruleset_name="if",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_aws_ec2_network_io,
)
