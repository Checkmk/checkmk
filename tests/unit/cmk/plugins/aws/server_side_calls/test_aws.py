#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any
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
                "auth": (
                    "access_key",
                    {
                        "access_key_id": "foo_key",
                        "secret_access_key": (
                            "cmk_postprocessed",
                            "explicit_password",
                            ("uuideb246734-2815-41fe-afbe-d420ed72e81a", "foo_pass"),
                        ),
                    },
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
                    "global_service_region": "us-gov-east-1",
                },
                "global_services": {
                    "ce": None,
                    "cloudfront": {
                        "selection": ("tags", [("cloudfront", ["tag", "tag2"])]),
                        "host_assignment": "domain_host",
                    },
                },
                "regions": ["ap-northeast-2", "ap-southeast-2"],
                "regional_services": {
                    "ec2": {
                        "selection": (
                            "tags",
                            [("ec2_key", ["tag1"]), ("ec2_key_2", ["tag1", "tag2"])],
                        ),
                        "limits": True,
                    },
                    "ebs": {"selection": "all", "limits": True},
                    "s3": {"selection": "all", "limits": True, "requests": None},
                    "glacier": {"selection": "all", "limits": True},
                    "elbv2": {"selection": ("tags", []), "limits": True},
                    "rds": {
                        "selection": (
                            "names",
                            ["explicit_rds_name1", "explicit_rds_name2"],
                        ),
                        "limits": True,
                    },
                    "cloudwatch_alarms": {"alarms": ("names", ["explicit_cloudwatch_name"])},
                    "dynamodb": {"selection": "all", "limits": True},
                    "wafv2": {"selection": "all", "cloudfront": None},
                    "lambda": {"selection": "all", "limits": True},
                    "ecs": {"selection": "all", "limits": True},
                    "elasticache": {"selection": "all", "limits": True},
                },
                "piggyback_naming_convention": "private_dns_name",
                "overall_tags": [("global_restrict_key", ["value1"])],
            },
            [
                "--access-key-id",
                "foo_key",
                "--secret-access-key-reference",
                ANY,
                "--proxy-host",
                "proxy_host",
                "--proxy-user",
                "foo_username",
                "--proxy-password-reference",
                ANY,
                "--global-service-region",
                "us-gov-east-1",
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
                "--cloudfront-host-assignment",
                "domain_host",
                "--overall-tag-key",
                "global_restrict_key",
                "--overall-tag-values",
                "value1",
                "--ignore-all-tags",
                "--hostname",
                "foo",
                "--piggyback-naming-convention",
                "private_dns_name",
            ],
            id="full_config_access_key",
        ),
        pytest.param(
            {
                "auth": (
                    "access_key_sts",
                    {
                        "access_key_id": "foo_key",
                        "secret_access_key": (
                            "cmk_postprocessed",
                            "explicit_password",
                            ("uuideb246734-2815-41fe-afbe-d420ed72e81a", "foo_pass"),
                        ),
                        "role_arn_id": "foo_arn_id",
                        "external_id": "foo_external_id",
                    },
                ),
                "regional_services": {
                    "cloudwatch_alarms": {},
                },
                "piggyback_naming_convention": "ip_region_instance",
            },
            [
                "--access-key-id",
                "foo_key",
                "--secret-access-key-reference",
                ANY,
                "--assume-role",
                "--role-arn",
                "foo_arn_id",
                "--external-id",
                "foo_external_id",
                "--services",
                "cloudwatch_alarms",
                "--ignore-all-tags",
                "--hostname",
                "foo",
                "--piggyback-naming-convention",
                "ip_region_instance",
            ],
            id="minimal_config_acces_key_and_sts_no_cloudwatch_alarms",
        ),
        pytest.param(
            {
                "auth": (
                    "sts",
                    {"role_arn_id": "foo_arn_id", "external_id": "foo_external_id"},
                ),
                "regional_services": {
                    "cloudwatch_alarms": {"alarms": "all"},
                },
                "piggyback_naming_convention": "ip_region_instance",
            },
            [
                "--assume-role",
                "--role-arn",
                "foo_arn_id",
                "--external-id",
                "foo_external_id",
                "--services",
                "cloudwatch_alarms",
                "--cloudwatch-alarms",
                "--ignore-all-tags",
                "--hostname",
                "foo",
                "--piggyback-naming-convention",
                "ip_region_instance",
            ],
            id="minimal_config_sts_all_cloudwatch_alarms",
        ),
        pytest.param(
            {
                "auth": ("none"),
                "proxy_details": {
                    "proxy_host": "1.1.1",
                    "proxy_user": "banana",
                    "proxy_password": (
                        "cmk_postprocessed",
                        "stored_password",
                        ("banana123", ""),
                    ),
                },
                "piggyback_naming_convention": "ip_region_instance",
            },
            [
                "--proxy-host",
                "1.1.1",
                "--proxy-user",
                "banana",
                "--proxy-password-reference",
                ANY,
                "--ignore-all-tags",
                "--hostname",
                "foo",
                "--piggyback-naming-convention",
                "ip_region_instance",
            ],
            id="minimal_config_without_auth",
        ),
        pytest.param(
            {
                "auth": ("none"),
                "proxy_details": {
                    "proxy_host": "1.1.1",
                    "proxy_user": "banana",
                    "proxy_password": (
                        "cmk_postprocessed",
                        "stored_password",
                        ("banana123", ""),
                    ),
                },
                "piggyback_naming_convention": "ip_region_instance",
                "import_tags": ("all_tags", None),
            },
            [
                "--proxy-host",
                "1.1.1",
                "--proxy-user",
                "banana",
                "--proxy-password-reference",
                ANY,
                "--hostname",
                "foo",
                "--piggyback-naming-convention",
                "ip_region_instance",
            ],
            id="minimal_config_import_all_tags",
        ),
        pytest.param(
            {
                "auth": ("none"),
                "proxy_details": {
                    "proxy_host": "1.1.1",
                    "proxy_user": "banana",
                    "proxy_password": (
                        "cmk_postprocessed",
                        "stored_password",
                        ("banana123", ""),
                    ),
                },
                "piggyback_naming_convention": "ip_region_instance",
                "import_tags": ("filter_tags", "foo:bar"),
            },
            [
                "--proxy-host",
                "1.1.1",
                "--proxy-user",
                "banana",
                "--proxy-password-reference",
                ANY,
                "--import-matching-tags-as-labels",
                "foo:bar",
                "--hostname",
                "foo",
                "--piggyback-naming-convention",
                "ip_region_instance",
            ],
            id="minimal_config_import_filtered_tags",
        ),
    ],
)
def test_values_to_args(value: Mapping[str, Any], expected_args: Sequence[Any]) -> None:
    # GIVEN
    params = process_configuration_to_parameters(value)

    # WHEN
    special_agent_calls = list(special_agent_aws(params.value, HostConfig(name="foo")))

    # THEN
    assert len(special_agent_calls) == 1
    special_agent_call = special_agent_calls[0]
    assert special_agent_call.command_arguments == expected_args
