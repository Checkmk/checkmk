#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Sequence
from unittest.mock import ANY

import pytest

from cmk.plugins.aws.server_side_calls.aws_agent_call import special_agent_aws
from cmk.server_side_calls.v1 import HostConfig
from cmk.server_side_calls_backend.config_processing import process_configuration_to_parameters


@pytest.mark.parametrize(
    ["value", "expected_args"],
    [
        pytest.param(
            {
                "access_key_id": "foo_key",
                "secret_access_key": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuideb246734-2815-41fe-afbe-d420ed72e81a", "foo_pass"),
                ),
                "proxy_details": {
                    "proxy_host": "proxy_host",
                    "proxy_user": "foo_username",
                    "proxy_password": (
                        "cmk_postprocessed",
                        "explicit_password",
                        ("uuidbc10387e-9a3e-4920-9918-3eb5a3669202", "foo_proxy_pw"),
                    ),
                },
                "access": {
                    "global_service_region": "us_gov_east_1",
                    "role_arn_id": {"role_arn": "foo_iam", "external_id": "foo_external_id"},
                },
                "global_services": {
                    "ce": ("all", {}),
                    "route53": ("none", None),
                    "cloudfront": (
                        "tags",
                        {
                            "tags": [{"key": "cloudfront", "values": ["tag", "tag2"]}],
                            "host_assignment": "domain_host",
                        },
                    ),
                },
                "regions_to_monitor": ["ap_northeast_2", "ap_southeast_2"],
                "services": {
                    "ec2": (
                        "tags",
                        {
                            "tags": [
                                {"key": "ec2_key", "values": ["tag1"]},
                                {"key": "ec2_key_2", "values": ["tag1", "tag2"]},
                            ],
                            "limits": "limits",
                        },
                    ),
                    "ebs": ("all", {"limits": "limits"}),
                    "s3": ("all", {"limits": "limits", "requests": None}),
                    "glacier": ("all", {"limits": "limits"}),
                    "elb": ("none", None),
                    "elbv2": ("tags", {"tags": [], "limits": "limits"}),
                    "rds": (
                        "names",
                        {"names": ["explicit_rds_name1", "explicit_rds_name2"], "limits": "limits"},
                    ),
                    "cloudwatch_alarms": (
                        "names",
                        {"names": ["explicit_cloudwatch_name"], "limits": "no_limits"},
                    ),
                    "dynamodb": ("all", {"limits": "limits"}),
                    "wafv2": ("all", {"limits": "no_limits", "cloudfront": None}),
                    "aws_lambda": ("all", {"limits": "limits"}),
                    "sns": ("none", None),
                    "ecs": ("all", {"limits": "limits"}),
                    "elasticache": ("all", {"limits": "limits"}),
                },
                "piggyback_naming_convention": "private_dns_name",
                "overall_tags": [{"key": "global_restrict_key", "values": ["value1"]}],
            },
            [
                "--access-key-id",
                "foo_key",
                "--secret-access-key",
                ANY,
                "--proxy-host",
                "proxy_host",
                "--proxy-user",
                "foo_username",
                "--proxy-password",
                ANY,
                "--global-service-region",
                "us-gov-east-1",
                "--assume-role",
                "--role-arn",
                "foo_iam",
                "--external-id",
                "foo_external_id",
                "--regions",
                "ap-northeast-2",
                "ap-southeast-2",
                "--global-services",
                "ce",
                "cloudfront",
                "--cloudfront-tag-key",
                "cloudfront",
                "--cloudfront-tag-values",
                "tag",
                "tag2",
                "--cloudfront-host-assignment",
                "domain_host",
                "--services",
                "cloudwatch_alarms",
                "dynamodb",
                "ebs",
                "ec2",
                "ecs",
                "elasticache",
                "elbv2",
                "glacier",
                "lambda",
                "rds",
                "s3",
                "wafv2",
                "--ec2-limits",
                "--ec2-tag-key",
                "ec2_key",
                "--ec2-tag-values",
                "tag1",
                "--ec2-tag-key",
                "ec2_key_2",
                "--ec2-tag-values",
                "tag1",
                "tag2",
                "--ebs-limits",
                "--s3-limits",
                "--glacier-limits",
                "--elbv2-limits",
                "--rds-limits",
                "--rds-names",
                "explicit_rds_name1",
                "explicit_rds_name2",
                "--cloudwatch-alarms",
                "explicit_cloudwatch_name",
                "--dynamodb-limits",
                "--lambda-limits",
                "--ecs-limits",
                "--elasticache-limits",
                "--s3-requests",
                "--wafv2-cloudfront",
                "--overall-tag-key",
                "global_restrict_key",
                "--overall-tag-values",
                "value1",
                "--hostname",
                "foo",
                "--piggyback-naming-convention",
                "private_dns_name",
            ],
            id="full_config",
        ),
        pytest.param(
            {
                "access_key_id": "strawberry",
                "secret_access_key": (
                    "cmk_postprocessed",
                    "stored_password",
                    ("strawberry098", ""),
                ),
                "proxy_details": {
                    "proxy_host": "1.1.1",
                    "proxy_user": "banana",
                    "proxy_password": ("cmk_postprocessed", "stored_password", ("banana123", "")),
                },
                "access": {},
                "global_services": {},
                "regions_to_monitor": [],
                "services": {},
                "piggyback_naming_convention": "checkmk_mix",
            },
            [
                "--access-key-id",
                "strawberry",
                "--secret-access-key",
                ANY,
                "--proxy-host",
                "1.1.1",
                "--proxy-user",
                "banana",
                "--proxy-password",
                ANY,
                "--hostname",
                "foo",
                "--piggyback-naming-convention",
                "checkmk_mix",
            ],
            id="passwords_from_store",
        ),
    ],
)
def test_fs_values_to_args(value: Mapping[str, Any], expected_args: Sequence[Any]) -> None:
    # GIVEN
    params = process_configuration_to_parameters(value)

    # WHEN
    special_agent_calls = list(special_agent_aws(params.value, HostConfig(name="foo")))

    # THEN
    assert len(special_agent_calls) == 1
    special_agent_call = special_agent_calls[0]
    assert special_agent_call.command_arguments == expected_args
