#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.plugins.wato.special_agents.aws import _migrate
from cmk.plugins.aws.server_side_calls.aws_agent_call import AwsParams
from cmk.server_side_calls.v1 import Secret

ACCESS_KEY_ID = "XYZABC123"
ACCESS_KEY_SECRET = (
    "cmk_postprocessed",
    "stored_password",
    ("password_aws", ""),
)

PROCESSED_ACCESS_KEY_SECRET = Secret(id=0)

ROLE_ARN_ID = "arn:aws:iam::AWSID:role/Rolename"
EXTERNAL_ID = "UniqueExternalIdFrom-4080-3046-6243"

AUTH_ACCESS_KEY = (
    "access_key",
    {
        "access_key_id": ACCESS_KEY_ID,
        "secret_access_key": ACCESS_KEY_SECRET,
    },
)

AUTH_ACCESS_KEY_STS = (
    "access_key_sts",
    {
        "access_key_id": ACCESS_KEY_ID,
        "secret_access_key": ACCESS_KEY_SECRET,
        "role_arn_id": ROLE_ARN_ID,
        "external_id": EXTERNAL_ID,
    },
)


AUTH_STS = (
    "sts",
    {"role_arn_id": ROLE_ARN_ID, "external_id": EXTERNAL_ID},
)


@pytest.mark.parametrize(
    ["value", "expected"],
    [
        pytest.param(
            {
                "access_key_id": ACCESS_KEY_ID,
                "secret_access_key": ACCESS_KEY_SECRET,
                "access": {"role_arn_id": (ROLE_ARN_ID, EXTERNAL_ID)},
            },
            {"access": {}, "auth": AUTH_ACCESS_KEY_STS},
            id="minimal_config_with_access_key_and_assume_role",
        ),
        pytest.param(
            {
                "access_key_id": ACCESS_KEY_ID,
                "secret_access_key": ACCESS_KEY_SECRET,
                "access": {},
            },
            {
                "access": {},
                "auth": AUTH_ACCESS_KEY,
            },
            id="minimal_config_with_access_key",
        ),
        pytest.param(
            {
                "access_key_id": ACCESS_KEY_ID,
                "secret_access_key": ACCESS_KEY_SECRET,
                "access": {},
                "global_services": {
                    "ce": None,
                    "route53": None,
                    "cloudfront": {"selection": "all", "host_assignment": "aws_host"},
                },
                "regions": ["eu-central-1", "eu-west-1"],
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
                "import_tags": ("filter_tags", "foo:bar"),
            },
            {
                "access": {},
                "auth": AUTH_ACCESS_KEY,
                "global_services": {
                    "ce": None,
                    "route53": None,
                    "cloudfront": {"selection": "all", "host_assignment": "aws_host"},
                },
                "regions": ["eu-central-1", "eu-west-1"],
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
                "import_tags": ("filter_tags", "foo:bar"),
            },
            id="max_config_with_access_key",
        ),
        pytest.param(
            {
                "access_key_id": ACCESS_KEY_ID,
                "secret_access_key": ACCESS_KEY_SECRET,
                "access": {},
                "global_services": {
                    "ce": None,
                    "route53": None,
                    "cloudfront": {"selection": "all", "host_assignment": "aws_host"},
                },
                "regions": ["eu-central-1", "eu-west-1"],
                "services": {
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
            },
            {
                "access": {},
                "auth": AUTH_ACCESS_KEY,
                "global_services": {
                    "ce": None,
                    "route53": None,
                    "cloudfront": {"selection": "all", "host_assignment": "aws_host"},
                },
                "regions": ["eu-central-1", "eu-west-1"],
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
                "import_tags": ("all_tags", None),
            },
            id="max_config_old_services_key",
        ),
    ],
)
def test_migrate(value: dict, expected: dict[str, object]) -> None:
    params = _migrate(value)

    assert params == expected


@pytest.mark.parametrize(
    ["value"],
    [
        pytest.param(
            {
                "access": {},
                "auth": "none",
                "piggyback_naming_convention": "ip_region_instance",
            },
            id="model_validate_AuthNone",
        ),
        pytest.param(
            {
                "access": {},
                "auth": AUTH_STS,
                "piggyback_naming_convention": "ip_region_instance",
            },
            id="model_validate_AuthSts",
        ),
        pytest.param(
            {
                "access": {},
                "auth": (
                    "access_key_sts",
                    {
                        "access_key_id": ACCESS_KEY_ID,
                        "secret_access_key": PROCESSED_ACCESS_KEY_SECRET,
                        "role_arn_id": ROLE_ARN_ID,
                        "external_id": EXTERNAL_ID,
                    },
                ),
                "piggyback_naming_convention": "ip_region_instance",
            },
            id="model_validate_AuthAccessKey",
        ),
        pytest.param(
            {
                "access": {},
                "auth": (
                    "access_key",
                    {
                        "access_key_id": ACCESS_KEY_ID,
                        "secret_access_key": PROCESSED_ACCESS_KEY_SECRET,
                    },
                ),
                "piggyback_naming_convention": "ip_region_instance",
            },
            id="model_validate_AuthAccessKeySts",
        ),
    ],
)
def test_auth_pydantic_model(value: dict) -> None:
    AwsParams.model_validate(value)
