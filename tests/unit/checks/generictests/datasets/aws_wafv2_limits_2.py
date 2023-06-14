#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "aws_wafv2_limits"

info = [
    [
        '[["web_acl_capacity_units",',
        '"Web',
        "ACL",
        "capacity",
        "units",
        '(WCUs)",',
        "1500,",
        "2,",
        '"eu-central-1"]]',
    ]
]

discovery = {"": [("eu-central-1", {})]}

checks = {
    "": [
        (
            "eu-central-1",
            {
                "web_acls": (None, 80.0, 90.0),
                "rule_groups": (None, 80.0, 90.0),
                "ip_sets": (None, 80.0, 90.0),
                "regex_pattern_sets": (None, 80.0, 90.0),
                "web_acl_capacity_units": (None, 80.0, 90.0),
            },
            [
                (0, "No levels reached", [("aws_wafv2_web_acl_capacity_units", 2)]),
                (0, "\nWeb ACL capacity units (WCUs): 2 (of max. 1500)"),
            ],
        )
    ]
}
