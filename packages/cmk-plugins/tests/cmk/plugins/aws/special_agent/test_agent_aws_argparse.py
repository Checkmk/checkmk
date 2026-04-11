#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

import pytest

import cmk.plugins.aws.special_agent.agent_aws as agent
from cmk.plugins.aws.special_agent.agent_aws import parse_arguments

# These have to always exist, so just set them here
REQUIRED_ARGS = ["--hostname", "foo", "--piggyback-naming-convention", "ip_region_instance"]


@pytest.mark.parametrize(
    "args, expected",
    [
        (
            REQUIRED_ARGS,
            {
                "hostname": "foo",
                "piggyback_naming_convention": agent.NamingConvention.ip_region_instance,
                "tag_key_pattern": agent.TagsImportPatternOption.import_all,
            },
        ),
        (
            REQUIRED_ARGS
            + [
                "--region",
                "af-south-1",
                "--region",
                "ap-east-1",
                "--region",
                "us-west-2",
                "--wafv2-cloudfront",
            ],
            {
                "hostname": "foo",
                "piggyback_naming_convention": agent.NamingConvention.ip_region_instance,
                "tag_key_pattern": agent.TagsImportPatternOption.import_all,
                "regions": ["af-south-1", "ap-east-1", "us-west-2"],
                "wafv2_cloudfront": True,
            },
        ),
        (
            REQUIRED_ARGS
            + [
                "--region",
                "af-south-1",
                "--region",
                "ap-east-1",
                "--global-service",
                "ce",
                "--global-service",
                "cloudfront",
                "--service",
                "ebs",
                "--service",
                "s3",
                "--wafv2-cloudfront",
                "--cloudwatch-alarm",
                "alarm1",
                "--cloudwatch-alarm",
                "well-thats-quite-alarming",
                "--overall-tag-key",
                "ohno",
                "--overall-tag-value",
                "mehr",
                "--overall-tag-value",
                "Werte",
                "--overall-tag-value",
                "auch",
                "--overall-tag-value",
                "auf",
                "--overall-tag-value",
                "Deutsch!",
                "--s3-name",
                "no",
                "--s3-name",
                "nargs",
                "--s3-limits",
            ],
            {
                "hostname": "foo",
                "piggyback_naming_convention": agent.NamingConvention.ip_region_instance,
                "tag_key_pattern": agent.TagsImportPatternOption.import_all,
                "regions": ["af-south-1", "ap-east-1"],
                "global_services": ["ce", "cloudfront"],
                "services": ["ebs", "s3"],
                "wafv2_cloudfront": True,
                "cloudwatch_alarms": ["alarm1", "well-thats-quite-alarming"],
                "overall_tag_keys": ["ohno"],
                "overall_tag_values": [
                    "mehr",
                    "Werte",
                    "auch",
                    "auf",
                    "Deutsch!",
                ],
                "s3_names": ["no", "nargs"],
                "s3_limits": True,
            },
        ),
    ],
)
def test_parse_arguments(args: Sequence[str], expected: Mapping[str, Any]) -> None:  # type: ignore[misc]
    ns = parse_arguments(args)
    for prop, value in expected.items():
        assert getattr(ns, prop) == value
