#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.aws.special_agent.agent_aws import filter_resources_matching_tags, Tags


@pytest.mark.parametrize(
    "resource_tags, tags_to_match, expected_result",
    [
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": "no-match-value"}],
                "ARN2": [
                    {"Key": "tag-key2", "Value": "no-match-value"},
                    {"Key": "tag-key", "Value": "match-value"},
                ],
            },
            [{"Key": "tag-key", "Value": "match-value"}],
            {"ARN2"},
        ),
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": "no-match-value"}],
            },
            [{"Key": "tag-key", "Value": "match-value"}],
            set(),
        ),
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": "no-match-value"}],
                "ARN2": [
                    {"Key": "tag-key2", "Value": "match-value2"},
                    {"Key": "tag-key", "Value": "match-value"},
                ],
            },
            [
                {"Key": "tag-key", "Value": "match-value"},
                {"Key": "tag-key2", "Value": "match-value2"},
            ],
            {"ARN2"},
        ),
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": "match-value"}],
                "ARN2": [
                    {"Key": "tag-key2", "Value": "match-value2"},
                    {"Key": "tag-key", "Value": "match-value"},
                ],
            },
            [
                {"Key": "tag-key", "Value": "match-value"},
                {"Key": "tag-key2", "Value": "match-value2"},
            ],
            {"ARN1", "ARN2"},
        ),
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": ""}],
            },
            [
                {"Key": "tag-key", "Value": "match-value"},
            ],
            set(),
        ),
        (
            {
                "ARN1": [],
            },
            [
                {"Key": "tag-key", "Value": "match-value"},
            ],
            set(),
        ),
        (
            {
                "ARN1": [],
            },
            [],
            set(),
        ),
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": ""}],
            },
            [],
            set(),
        ),
    ],
)
def test_filter_resources_matching_tags(
    resource_tags: dict[str, Tags],
    tags_to_match: Tags,
    expected_result: set[str],
) -> None:
    assert filter_resources_matching_tags(resource_tags, tags_to_match) == expected_result
