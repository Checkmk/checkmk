#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "aws_wafv2_limits"

info = [
    [
        '[["web_acls",',
        '"Web',
        'ACLs",',
        "100,",
        "1,",
        '"CloudFront"],',
        '["rule_groups",',
        '"Rule',
        'groups",',
        "100,",
        "1,",
        '"CloudFront"],',
        '["ip_sets",',
        '"IP',
        'sets",',
        "100,",
        "0,",
        '"CloudFront"],',
        '["regex_pattern_sets",',
        '"Regex',
        'sets",',
        "10,",
        "1,",
        '"CloudFront"]]',
    ],
    [
        '[["web_acls",',
        '"Web',
        'ACLs",',
        "100,",
        "1,",
        '"eu-central-1"],',
        '["rule_groups",',
        '"Rule',
        'groups",',
        "100,",
        "1,",
        '"eu-central-1"],',
        '["ip_sets",',
        '"IP',
        'sets",',
        "100,",
        "1,",
        '"eu-central-1"],',
        '["regex_pattern_sets",',
        '"Regex',
        'sets",',
        "10,",
        "1,",
        '"eu-central-1"]]',
    ],
    [
        '[["web_acls",',
        '"Web',
        'ACLs",',
        "100,",
        "1,",
        '"us-east-1"],',
        '["rule_groups",',
        '"Rule',
        'groups",',
        "100,",
        "0,",
        '"us-east-1"],',
        '["ip_sets",',
        '"IP',
        'sets",',
        "100,",
        "1,",
        '"us-east-1"],',
        '["regex_pattern_sets",',
        '"Regex',
        'sets",',
        "10,",
        "0,",
        '"us-east-1"]]',
    ],
]

discovery = {"": [("CloudFront", {}), ("eu-central-1", {}), ("us-east-1", {})]}

checks = {
    "": [
        (
            "CloudFront",
            {
                "web_acls": (None, 80.0, 90.0),
                "rule_groups": (None, 80.0, 90.0),
                "ip_sets": (None, 80.0, 90.0),
                "regex_pattern_sets": (None, 80.0, 90.0),
                "web_acl_capacity_units": (None, 80.0, 90.0),
            },
            [
                (
                    0,
                    "No levels reached",
                    [
                        ("aws_wafv2_web_acls", 1),
                        ("aws_wafv2_rule_groups", 1),
                        ("aws_wafv2_ip_sets", 0),
                        ("aws_wafv2_regex_pattern_sets", 1),
                    ],
                ),
                (0, "\nIP sets: 0 (of max. 100)"),
                (0, "\nRegex sets: 1 (of max. 10)"),
                (0, "\nRule groups: 1 (of max. 100)"),
                (0, "\nWeb ACLs: 1 (of max. 100)"),
            ],
        ),
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
                (
                    0,
                    "No levels reached",
                    [
                        ("aws_wafv2_web_acls", 1),
                        ("aws_wafv2_rule_groups", 1),
                        ("aws_wafv2_ip_sets", 1),
                        ("aws_wafv2_regex_pattern_sets", 1),
                    ],
                ),
                (0, "\nIP sets: 1 (of max. 100)"),
                (0, "\nRegex sets: 1 (of max. 10)"),
                (0, "\nRule groups: 1 (of max. 100)"),
                (0, "\nWeb ACLs: 1 (of max. 100)"),
            ],
        ),
    ]
}
