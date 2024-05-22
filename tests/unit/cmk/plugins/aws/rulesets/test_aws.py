#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import importlib
import sys
from typing import Generator

import pytest
from pytest import MonkeyPatch

from cmk.utils.version import Edition, edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

import cmk.plugins.aws.rulesets.aws as aws_ruleset

AWS_VS_RULE_VALUE = {
    "access_key_id": "foo_key",
    "secret_access_key": ("password", "foo_pass"),
    "proxy_details": {
        "proxy_host": "proxy_host",
        "proxy_user": "foo_username",
        "proxy_password": ("password", "foo_proxy_pw"),
    },
    "access": {
        "global_service_region": "us-gov-east-1",
        "role_arn_id": ("foo_iam", "foo_external_id"),
    },
    "global_services": {
        "ce": None,
        "cloudfront": {
            "selection": ("tags", [("cloudfront", ["tag", "tag2"])]),
            "host_assignment": "domain_host",
        },
    },
    "regions": ["ap-northeast-2", "ap-southeast-2"],
    "services": {
        "ec2": {
            "selection": ("tags", [("ec2_key", ["tag1"]), ("ec2_key_2", ["tag1", "tag2"])]),
            "limits": True,
        },
        "ebs": {"selection": "all", "limits": True},
        "s3": {"selection": "all", "limits": True, "requests": None},
        "glacier": {"selection": "all", "limits": True},
        "elbv2": {"selection": ("tags", []), "limits": True},
        "rds": {
            "selection": ("names", ["explicit_rds_name1", "explicit_rds_name2"]),
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
}


def test_vs_to_fs_rule_update_valid_datatypes() -> None:
    # GIVEN
    valuespec = convert_to_legacy_rulespec(
        aws_ruleset.rule_spec_aws, Edition.CRE, lambda x: x
    ).valuespec

    # WHEN
    value = valuespec.transform_value(AWS_VS_RULE_VALUE)
    valuespec.validate_datatype(value, "")

    # THEN
    assert value["access_key_id"] == "foo_key"
    access_key = value["secret_access_key"]
    assert access_key[1] == "explicit_password"
    assert access_key[2][1] == "foo_pass"
    assert value["global_services"]["ce"] == ("all", {})
    assert value["access"]["global_service_region"] == "us_gov_east_1"
    assert value["regions_to_monitor"] == ["ap_northeast_2", "ap_southeast_2"]
    assert value["overall_tags"] == [{"key": "global_restrict_key", "values": ["value1"]}]
    if edition() is Edition.CCE:
        assert value["global_services"]["route53"] == ("none", None)
        assert value["services"]["aws_lambda"] == ("all", {"limits": "limits"})


@pytest.fixture(autouse=True)
def reset_cce_module() -> Generator[None, None, None]:
    yield

    importlib.reload(aws_ruleset)


def test_cce_to_non_cce_rule_drops_services(monkeypatch: MonkeyPatch) -> None:
    # GIVEN
    monkeypatch.setitem(sys.modules, "cmk.plugins.aws.rulesets.cce", None)
    importlib.reload(aws_ruleset)

    valuespec = convert_to_legacy_rulespec(
        aws_ruleset.rule_spec_aws, Edition.CRE, lambda x: x
    ).valuespec

    # WHEN
    value = valuespec.transform_value(AWS_VS_RULE_VALUE)

    # THEN
    assert "route53" not in value["global_services"]
    assert "cloudfront" not in value["global_services"]
    assert "aws_lambda" not in value["services"]
    assert "sns" not in value["services"]
    assert "ecs" not in value["services"]
    assert "elasticache" not in value["services"]
