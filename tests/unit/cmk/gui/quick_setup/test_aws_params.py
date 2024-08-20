#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.quick_setup.config_setups.aws.stages import aws_transform_to_disk

QUICK_SETUP_PARAMS = {
    "access_key_id": "my_access_key",
    "secret_access_key": (
        "cmk_postprocessed",
        "explicit_password",
        (
            "uuidca5b9c84-1faa-4e42-a5a3-10ca28bb8dba",
            "my_secret_access_key",
        ),
    ),
    "regions_to_monitor": ["eu_central_1"],
    "global_services": ["ce", "route53", "cloudfront"],
    "services": [
        "ec2",
        "ebs",
        "s3",
        "glacier",
        "elb",
        "elbv2",
        "rds",
        "cloudwatch_alarms",
        "dynamodb",
        "wafv2",
        "aws_lambda",
        "sns",
        "ecs",
        "elasticache",
    ],
    "overall_tags": [{"key": "foo", "values": ["a", "b"]}],
}

EXPECTED_PARAMS = {
    "access_key_id": "my_access_key",
    "secret_access_key": (
        "cmk_postprocessed",
        "explicit_password",
        ("uuidca5b9c84-1faa-4e42-a5a3-10ca28bb8dba", "my_secret_access_key"),
    ),
    "access": {},
    "global_services": {
        "ce": ("all", {}),
        "route53": ("all", {}),
        "cloudfront": ("all", {"host_assignment": "aws_host"}),
    },
    "regions_to_monitor": ["eu_central_1"],
    "services": {
        "ec2": ("all", {"limits": "limits"}),
        "ebs": ("all", {"limits": "limits"}),
        "s3": ("all", {"limits": "limits"}),
        "glacier": ("all", {"limits": "limits"}),
        "elb": ("all", {"limits": "limits"}),
        "elbv2": ("all", {"limits": "limits"}),
        "rds": ("all", {"limits": "limits"}),
        "cloudwatch_alarms": ("all", {"limits": "limits"}),
        "dynamodb": ("all", {"limits": "limits"}),
        "wafv2": ("all", {"limits": "limits"}),
        "aws_lambda": ("all", {"limits": "limits"}),
        "sns": ("all", {"limits": "limits"}),
        "ecs": ("all", {"limits": "limits"}),
        "elasticache": ("all", {"limits": "limits"}),
    },
    "piggyback_naming_convention": "ip_region_instance",
    "overall_tags": [{"key": "foo", "values": ["a", "b"]}],
}


def test_quick_setup_aws_transform_to_valuespec() -> None:
    assert aws_transform_to_disk(QUICK_SETUP_PARAMS) == EXPECTED_PARAMS
