#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import parse_aws
from cmk.base.config import check_info

from cmk.agent_based.v2 import IgnoreResultsError

# 'TargetGroups': [
#        {
#            'TargetGroupArn': 'string',
#            'TargetGroupName': 'string',
#            'Protocol': 'HTTP'|'HTTPS'|'TCP'|'TLS',
#            'Port': 123,
#            'VpcId': 'string',
#            'HealthCheckProtocol': 'HTTP'|'HTTPS'|'TCP'|'TLS',
#            'HealthCheckPort': 'string',
#            'HealthCheckEnabled': True|False,
#            'HealthCheckIntervalSeconds': 123,
#            'HealthCheckTimeoutSeconds': 123,
#            'HealthyThresholdCount': 123,
#            'UnhealthyThresholdCount': 123,
#            'HealthCheckPath': 'string',
#            'Matcher': {
#                'HttpCode': 'string'
#            },
#            'LoadBalancerArns': [
#                'string',
#            ],
#            'TargetType': 'instance'|'ip'|'lambda'
#            'TargetHealth': {
#                'State': 'initial'|'healthy'|'unhealthy'|'unused'|'draining'|'unavailable',
#                'Reason': 'Elb.RegistrationInProgress'|'Elb.InitialHealthChecking'|'Target.ResponseCodeMismatch'|
#                          'Target.Timeout'|'Target.FailedHealthChecks'|'Target.NotRegistered'|'Target.NotInUse'|
#                          'Target.DeregistrationInProgress'|'Target.InvalidState'|'Target.IpUnusable'|
#                          'Target.HealthCheckDisabled'|'Elb.InternalError',
#                'Description': 'string'
#            },
#        },


def parse_aws_elbv2_target_groups(string_table):
    application_target_groups, network_target_groups = [], []
    for load_balancer_type, target_groups in parse_aws(string_table):
        if load_balancer_type == "application":
            application_target_groups.extend(target_groups)
        elif load_balancer_type == "network":
            network_target_groups.extend(target_groups)
    return application_target_groups, network_target_groups


def check_aws_elbv2_target_groups(item, params, target_groups):
    if len(target_groups) == 0:
        raise IgnoreResultsError("Currently no data from AWS")

    target_groups_by_state = {}
    for target_group in target_groups:
        for target_health in target_group.get("TargetHealthDescriptions", []):
            target_groups_by_state.setdefault(
                target_health.get("TargetHealth", {}).get("State", "unknown"), []
            ).append(target_group)

    for state_readable, groups in target_groups_by_state.items():
        if state_readable in ["initial", "healthy", "unused", "draining", "unavailable"]:
            state = 0
        elif state_readable in ["unhealthy"]:
            state = 2
        else:
            state = 3
        yield state, f"{state_readable} ({len(groups)})"


def inventory_aws_application_elb_target_groups(parsed):
    application_target_groups, _network_target_groups = parsed
    if application_target_groups:
        return [(None, {})]
    return []


def check_aws_application_elb_target_groups(item, params, parsed):
    application_target_groups, _network_target_groups = parsed
    return check_aws_elbv2_target_groups(item, params, application_target_groups)


check_info["aws_elbv2_target_groups"] = LegacyCheckDefinition(
    parse_function=parse_aws_elbv2_target_groups,
    service_name="AWS/ApplicationELB Target Groups",
    discovery_function=inventory_aws_application_elb_target_groups,
    check_function=check_aws_application_elb_target_groups,
)


def inventory_aws_network_elb_target_groups(parsed):
    _application_target_groups, network_target_groups = parsed
    if network_target_groups:
        return [(None, {})]
    return []


def check_aws_network_elb_target_groups(item, params, parsed):
    _application_target_groups, network_target_groups = parsed
    return check_aws_elbv2_target_groups(item, params, network_target_groups)


check_info["aws_elbv2_target_groups.network"] = LegacyCheckDefinition(
    service_name="AWS/NetworkELB Target Groups",
    sections=["aws_elbv2_target_groups"],
    discovery_function=inventory_aws_network_elb_target_groups,
    check_function=check_aws_network_elb_target_groups,
)
