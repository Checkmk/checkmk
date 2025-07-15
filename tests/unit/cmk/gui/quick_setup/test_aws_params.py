#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import ANY

from cmk.gui.quick_setup.config_setups.aws.stages import aws_transform_to_disk
from cmk.plugins.aws.server_side_calls.aws_agent_call import special_agent_aws
from cmk.server_side_calls.v1 import HostConfig
from cmk.server_side_calls_backend.config_processing import process_configuration_to_parameters

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
    "overall_tags": {
        "restriction_tags": [{"key": "foo", "values": ["a", "b"]}],
        "import_tags": ("filter_tags", "foo:bar"),
    },
}

EXPECTED_RULE_PARAMS = {
    "auth": (
        "access_key",
        {
            "access_key_id": "my_access_key",
            "secret_access_key": (
                "cmk_postprocessed",
                "explicit_password",
                ("uuidca5b9c84-1faa-4e42-a5a3-10ca28bb8dba", "my_secret_access_key"),
            ),
        },
    ),
    "global_services": {
        "ce": None,
        "route53": None,
        "cloudfront": {
            "selection": "all",
            "host_assignment": "aws_host",
        },
    },
    "access": {},
    "regions": ["eu-central-1"],
    "regional_services": {
        "ec2": {"selection": "all", "limits": True},
        "ebs": {"selection": "all", "limits": True},
        "s3": {"selection": "all", "limits": True},
        "glacier": {"selection": "all", "limits": True},
        "elb": {"selection": "all", "limits": True},
        "elbv2": {"selection": "all", "limits": True},
        "rds": {"selection": "all", "limits": True},
        "cloudwatch_alarms": {"alarms": "all", "limits": True},
        "dynamodb": {"selection": "all", "limits": True},
        "wafv2": {"selection": "all", "limits": True, "cloudfront": None},
        "lambda": {"selection": "all", "limits": True},
        "sns": {"selection": "all", "limits": True},
        "ecs": {"selection": "all", "limits": True},
        "elasticache": {"selection": "all", "limits": True},
    },
    "piggyback_naming_convention": "ip_region_instance",
    "overall_tags": [("foo", ["a", "b"])],
    "import_tags": ("filter_tags", "foo:bar"),
}


def test_quick_setup_aws_transform_to_valuespec() -> None:
    assert aws_transform_to_disk(QUICK_SETUP_PARAMS) == EXPECTED_RULE_PARAMS


def test_quick_setup_aws_to_ssc() -> None:
    # GIVEN
    qs_params = aws_transform_to_disk(QUICK_SETUP_PARAMS)
    params = process_configuration_to_parameters(qs_params)

    # WHEN
    special_agent_calls = list(special_agent_aws(params.value, HostConfig(name="foo")))

    # THEN
    assert len(special_agent_calls) == 1
    special_agent_call = special_agent_calls[0]
    assert special_agent_call.command_arguments == [
        "--access-key-id",
        "my_access_key",
        "--secret-access-key-reference",
        ANY,
        "--regions",
        "eu-central-1",
        "--global-services",
        "ce",
        "cloudfront",
        "route53",
        "--services",
        "cloudwatch_alarms",
        "dynamodb",
        "ebs",
        "ec2",
        "ecs",
        "elasticache",
        "elb",
        "elbv2",
        "glacier",
        "lambda",
        "rds",
        "s3",
        "sns",
        "wafv2",
        "--ec2-limits",
        "--ebs-limits",
        "--s3-limits",
        "--glacier-limits",
        "--elb-limits",
        "--elbv2-limits",
        "--rds-limits",
        "--cloudwatch_alarms-limits",
        "--cloudwatch-alarms",
        "--dynamodb-limits",
        "--wafv2-limits",
        "--lambda-limits",
        "--sns-limits",
        "--ecs-limits",
        "--elasticache-limits",
        "--wafv2-cloudfront",
        "--cloudfront-host-assignment",
        "aws_host",
        "--overall-tag-key",
        "foo",
        "--overall-tag-values",
        "a",
        "b",
        "--import-matching-tags-as-labels",
        "foo:bar",
        "--hostname",
        "foo",
        "--piggyback-naming-convention",
        "ip_region_instance",
    ]
