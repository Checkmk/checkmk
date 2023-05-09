#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

from cmk.base.check_api import check_levels, get_percent_human_readable, MKCounterWrapped
from cmk.base.check_legacy_includes.aws import (
    aws_get_counts_rate_human_readable,
    inventory_aws_generic_single,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.aws import extract_aws_metrics_by_labels, parse_aws


def parse_aws_wafv2_web_acl(info):
    metrics = extract_aws_metrics_by_labels(["AllowedRequests", "BlockedRequests"], parse_aws(info))
    try:
        return list(metrics.values())[-1]
    except IndexError:
        return {}


def check_aws_wafv2_web_acl(item, params, parsed):
    if len(parsed) == 0:
        raise MKCounterWrapped("Currently no data from AWS")

    metric_ids = ["AllowedRequests", "BlockedRequests"]
    # the metrics used here are only reported if they are not zero
    metric_vals = [parsed.get(metric_id, 0) for metric_id in metric_ids]
    requests_total = sum(metric_vals)

    yield check_levels(
        requests_total,
        "aws_wafv2_requests_rate",
        None,
        infoname="Total requests",
        human_readable_func=aws_get_counts_rate_human_readable,
    )

    for metric_id, metric_val in zip(metric_ids, metric_vals):
        # split at uppercase letters
        metric_id_split = [s.lower() for s in re.split("([A-Z][^A-Z]*)", metric_id) if s]

        yield check_levels(
            metric_val,
            "aws_wafv2_%s_rate" % "_".join(metric_id_split),
            None,
            infoname=" ".join(metric_id_split).capitalize(),
            human_readable_func=aws_get_counts_rate_human_readable,
        )

        try:
            perc = 100 * metric_val / requests_total
        except ZeroDivisionError:
            perc = 0

        yield check_levels(
            perc,
            "aws_wafv2_%s_perc" % "_".join(metric_id_split),
            params.get("%s_perc" % "_".join(metric_id_split)),
            infoname="Percentage %s" % " ".join(metric_id_split),
            human_readable_func=get_percent_human_readable,
        )


check_info["aws_wafv2_web_acl"] = {
    "parse_function": parse_aws_wafv2_web_acl,
    "discovery_function": lambda p: inventory_aws_generic_single(
        p, ["AllowedRequests", "BlockedRequests"], requirement=any
    ),
    "check_function": check_aws_wafv2_web_acl,
    "service_name": "AWS/WAFV2 Web ACL Requests",
    "check_ruleset_name": "aws_wafv2_web_acl",
}
