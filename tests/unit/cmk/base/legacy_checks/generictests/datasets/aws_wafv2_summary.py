#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "aws_wafv2_summary"

# ARNs have been removed
info = [
    [
        '[{"Name":',
        '"joerg-herbel-acl-global",',
        '"Id":',
        '"3bdfbac2-026a-4afa-98b8-32dbf8dbdf1c",',
        '"DefaultAction":',
        '{"Allow":',
        "{}},",
        '"Description":',
        '"",',
        '"Rules":',
        '[{"Name":',
        '"rule-group-1",',
        '"Priority":',
        "0,",
        '"Statement":',
        '{"RuleGroupReferenceStatement":',
        "{}},",
        '"OverrideAction":',
        '{"None":',
        "{}},",
        '"VisibilityConfig":',
        '{"SampledRequestsEnabled":',
        "true,",
        '"CloudWatchMetricsEnabled":',
        "true,",
        '"MetricName":',
        '"rule-group-1"}}],',
        '"VisibilityConfig":',
        '{"SampledRequestsEnabled":',
        "true,",
        '"CloudWatchMetricsEnabled":',
        "true,",
        '"MetricName":',
        '"joerg-herbel-acl-global"},',
        '"Capacity":',
        "1,",
        '"Region":',
        '"CloudFront"}]',
    ],
    [
        '[{"Name":',
        '"joerg-herbel-acl",',
        '"Id":',
        '"36a44c6c-0ff1-4dbc-9cc5-6195f180e749",',
        '"DefaultAction":',
        '{"Allow":',
        "{}},",
        '"Description":',
        '"",',
        '"Rules":',
        '[{"Name":',
        '"rule-group",',
        '"Priority":',
        "0,",
        '"Statement":',
        '{"RuleGroupReferenceStatement":',
        "{}},",
        '"OverrideAction":',
        '{"None":',
        "{}},",
        '"VisibilityConfig":',
        '{"SampledRequestsEnabled":',
        "true,",
        '"CloudWatchMetricsEnabled":',
        "true,",
        '"MetricName":',
        '"rule-group"}}],',
        '"VisibilityConfig":',
        '{"SampledRequestsEnabled":',
        "true,",
        '"CloudWatchMetricsEnabled":',
        "true,",
        '"MetricName":',
        '"joerg-herbel-acl"},',
        '"Capacity":',
        "2,",
        '"Region":',
        '"eu-central-1"}]',
    ],
    [
        '[{"Name":',
        '"us-acl",',
        '"Id":',
        '"5d404b61-5552-4f1a-bea7-8c405a5deb66",',
        '"DefaultAction":',
        '{"Allow":',
        "{}},",
        '"Description":',
        '"America",',
        '"Rules":',
        "[],",
        '"VisibilityConfig":',
        '{"SampledRequestsEnabled":',
        "true,",
        '"CloudWatchMetricsEnabled":',
        "true,",
        '"MetricName":',
        '"us-acl"},',
        '"Capacity":',
        "0,",
        '"Region":',
        '"us-east-1"}]',
    ],
]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {},
            [
                (0, "Total number of Web ACLs: 3"),
                (0, "CloudFront: 1"),
                (0, "Europe (Frankfurt): 1"),
                (0, "US East (N. Virginia): 1"),
                (
                    0,
                    "\nCloudFront:\njoerg-herbel-acl-global -- Description: [no description], Number "
                    "of rules and rule groups: 1\nEurope (Frankfurt):\njoerg-herbel-acl -- Description: "
                    "[no description], Number of rules and rule groups: 1\nUS East (N. Virginia):\n"
                    "us-acl -- Description: America, Number of rules and rule groups: 0",
                ),
            ],
        )
    ]
}
