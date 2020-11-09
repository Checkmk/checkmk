#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import get_number_with_precision
from cmk.base.check_api import get_bytes_human_readable
from cmk.base.check_api import MKCounterWrapped
from cmk.base.check_api import get_percent_human_readable
from cmk.base.check_api import check_levels
from cmk.base.check_api import state_markers
from cmk.base.check_api import ServiceCheckResult
from typing import Dict, List, Union, Optional, Tuple, Callable, Iterable
import functools
import cmk.utils.aws_constants as agent_aws_types

AWSRegions = dict(agent_aws_types.AWSRegions)


def parse_aws(info):
    import json
    loaded = []
    for row in info:
        try:
            loaded.extend(json.loads(" ".join(row)))
        except (TypeError, IndexError):
            pass
    return loaded


def extract_aws_metrics_by_labels(expected_metric_names, parsed, extra_keys=None):
    if extra_keys is None:
        extra_keys = []
    values_by_labels: Dict[str, Dict] = {}
    for row in parsed:
        row_id = row['Id'].lower()
        row_label = row['Label']
        row_values = row['Values']
        for expected_metric_name in expected_metric_names:
            expected_metric_name_lower = expected_metric_name.lower()
            if not row_id.startswith(expected_metric_name_lower)\
               and not row_id.endswith(expected_metric_name_lower):
                continue

            try:
                # AWSSectionCloudwatch in agent_aws.py yields both the actual values of the metrics
                # as returned by Cloudwatch and the time period over which they were collected (for
                # example 600 s). However, only for metrics based on the "Sum" statistics, the
                # period is not None, because these metrics need to be divided by the period to
                # convert the metric value to a rate. For all other metrics, the time period is
                # None.
                value, time_period = row_values[0]
                if time_period is not None:
                    value /= time_period
            except IndexError:
                continue
            else:
                values_by_labels.setdefault(row_label, {})\
                                .setdefault(expected_metric_name, value)
        for extra_key in extra_keys:
            extra_value = row.get(extra_key)
            if extra_value is None:
                continue
            values_by_labels.setdefault(row_label, {})\
                            .setdefault(extra_key, extra_value)
    return values_by_labels


def inventory_aws_generic(parsed, required_metrics):
    for instance_name, instance in parsed.items():
        if all(required_metric in instance for required_metric in required_metrics):
            yield instance_name, {}


def inventory_aws_generic_single(parsed, required_metrics, requirement=all):
    if requirement(required_metric in parsed for required_metric in required_metrics):
        return [(None, {})]


def check_aws_elb_summary_generic(item, params, load_balancers):
    yield 0, "Balancers: %s" % len(load_balancers)

    balancers_by_avail_zone: Dict[str, List] = {}
    long_output = []
    for row in load_balancers:
        balancer_name = row['LoadBalancerName']
        avail_zones_txt = []
        for avail_zone in row['AvailabilityZones']:
            if isinstance(avail_zone, dict):
                # elb vs. elbv2
                # elb provides a list of zones, elbv2 a list of dicts
                # including zone name
                avail_zone = avail_zone['ZoneName']

            try:
                avail_zone_readable = "%s (%s)" % (AWSRegions[avail_zone[:-1]], avail_zone[-1])
            except KeyError:
                avail_zone_readable = 'unknown (%s)' % avail_zone

            balancers_by_avail_zone.setdefault(avail_zone_readable, []).append(balancer_name)
            avail_zones_txt.append(avail_zone_readable)
        long_output.append("Balancer: %s, Availability zones: %s"\
                           % (balancer_name, ", ".join(avail_zones_txt)))

    for avail_zone, balancers in sorted(balancers_by_avail_zone.items()):
        yield 0, "%s: %s" % (avail_zone, len(balancers))

    if long_output:
        yield 0, '\n%s' % '\n'.join(long_output)


# Some limit values have dynamic names, eg.
# 'Rules of VPC security group %s' % SECURITY_GROUP
# At the moment we exclude them in the performance data.  If it's
# a limit for a piggyback host, we do NOT exclude, eg. 'load_balancer_listeners'
# and 'load_balancer_registered_instances' per load balancer piggyback host
_exclude_aws_limits_perf_vars = [
    'vpc_sec_group_rules',
    'vpc_sec_groups',
    "if_vpc_sec_group",
]

AWSLimitsByRegion = Dict[str, List]


def _is_valid_aws_limits_perf_data(perfvar):
    if perfvar in _exclude_aws_limits_perf_vars:
        return False
    return True


def parse_aws_limits_generic(info):
    limits_by_region: AWSLimitsByRegion = {}
    for line in parse_aws(info):
        limits_by_region.setdefault(line[-1], []).append(line[:-1] + [lambda x: "%s" % x])
    return limits_by_region


def check_aws_limits(aws_service, params, parsed_region_data):
    """
    Generic check for checking limits of AWS resource.
    - levels: use plain resource_key
    - performance data: aws_%s_%s % AWS resource, resource_key
    """
    long_output = []
    levels_reached = set()
    max_state = 0
    perfdata = []
    for resource_key, resource_title, limit, amount, human_readable_func in parsed_region_data:

        try:
            p_limit, warn, crit = params[resource_key]
        except KeyError:
            yield 1, "Unknown resource %r" % str(resource_key)
            continue

        if p_limit is None:
            limit_ref = limit
        else:
            limit_ref = p_limit

        infotext = '%s: %s (of max. %s)' % (resource_title, human_readable_func(amount),
                                            human_readable_func(limit_ref))
        perfvar = "aws_%s_%s" % (aws_service, resource_key)
        if _is_valid_aws_limits_perf_data(resource_key):
            perfdata.append((perfvar, amount))

        if not limit_ref:
            continue

        state, extrainfo, _perfdata = check_levels(100.0 * amount / limit_ref,
                                                   None, (warn, crit),
                                                   human_readable_func=get_percent_human_readable,
                                                   infoname="Usage")

        max_state = max(state, max_state)
        if state:
            levels_reached.add(resource_title)
            infotext += ", %s%s" % (extrainfo, state_markers[state])
        long_output.append(infotext)

    if levels_reached:
        yield max_state, 'Levels reached: %s' % ", ".join(sorted(levels_reached)), perfdata
    else:
        yield 0, 'No levels reached', perfdata

    if long_output:
        yield 0, "\n%s" % "\n".join(sorted(long_output))


def aws_get_float_human_readable(f, unit=""):
    return get_number_with_precision(f, unit=unit, precision=3)


def aws_get_counts_rate_human_readable(rate):
    return aws_get_float_human_readable(rate)[:-1] + "/s"


def aws_get_bytes_rate_human_readable(rate):
    return get_bytes_human_readable(rate) + "/s"


def check_aws_request_rate(request_rate):
    return 0, 'Requests: %s' % aws_get_counts_rate_human_readable(request_rate), [
        ('requests_per_second', request_rate)
    ]


def check_aws_error_rate(error_rate, request_rate, metric_name_rate, metric_name_perc, levels,
                         display_text):

    yield (0, '%s: %s' % (display_text, aws_get_counts_rate_human_readable(error_rate)),
           [(metric_name_rate, error_rate)])

    try:
        errors_perc = 100.0 * error_rate / request_rate
    except ZeroDivisionError:
        errors_perc = 0

    yield check_levels(errors_perc,
                       metric_name_perc,
                       levels,
                       human_readable_func=get_percent_human_readable,
                       infoname="%s of total requests" % display_text)


def check_aws_http_errors(params,
                          parsed,
                          http_err_codes,
                          cloudwatch_metrics_format,
                          key_all_requests='RequestCount'):

    request_rate = parsed.get(key_all_requests)
    if request_rate is None:
        raise MKCounterWrapped("Currently no data from AWS")

    yield check_aws_request_rate(request_rate)

    for http_err_code in http_err_codes:
        # CloudWatch only reports HTTPCode_... if the value is nonzero
        for result in check_aws_error_rate(
                parsed.get(cloudwatch_metrics_format % http_err_code.upper(), 0), request_rate,
                'aws_http_%s_rate' % http_err_code, 'aws_http_%s_perc' % http_err_code,
                params.get('levels_http_%s_perc' % http_err_code),
                "%s-Errors" % http_err_code.upper()):
            yield result


def check_aws_metrics(
    metric_infos: List[Dict[str, Union[float, Optional[str], Optional[Tuple], Optional[Callable]]]]
) -> Iterable[ServiceCheckResult]:

    go_stale = True

    for metric_info in metric_infos:

        metric_val = metric_info['metric_val']
        if metric_val is None:
            continue
        go_stale = False

        yield check_levels(metric_val,
                           metric_info.get('metric_name'),
                           metric_info.get('levels'),
                           human_readable_func=metric_info.get('human_readable_func'),
                           infoname=metric_info.get('info_name'))

    if go_stale:
        raise MKCounterWrapped("Currently no data from AWS")


def aws_rds_service_item(instance_id, region):
    return '%s [%s]' % (instance_id, region)


def aws_get_parsed_item_data(check_function: Callable) -> Callable:
    """
    Modified version of get_parsed_item_data which lets services go stale instead of UNKN if the
    item is not found.
    """
    @functools.wraps(check_function)
    def wrapped_check_function(item, params, parsed):
        if not isinstance(parsed, dict):
            return 3, "Wrong usage of decorator function 'aws_get_parsed_item_data': parsed is " \
                      "not a dict"
        if item not in parsed:
            raise MKCounterWrapped("Currently no data from AWS")
        return check_function(item, params, parsed[item])

    return wrapped_check_function
