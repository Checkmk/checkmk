#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import MagicMock, patch

import pytest

from cmk.special_agents.agent_aws import fetch_resources_matching_tags


@pytest.mark.parametrize(
    "fetched_data, tags_to_match, expected_result",
    [
        (
            [
                {
                    "ResourceARN": "ARN1",
                    "Tags": [{"Key": "tag-key", "Value": "no-match-value"}],
                },
                {
                    "ResourceARN": "ARN2",
                    "Tags": [
                        {"Key": "tag-key2", "Value": "no-match-value"},
                        {"Key": "tag-key", "Value": "match-value"},
                    ],
                },
            ],
            [{"Key": "tag-key", "Value": "match-value"}],
            {"ARN2"},
        ),
        (
            [
                {
                    "ResourceARN": "ARN1",
                    "Tags": [{"Key": "tag-key", "Value": "no-match-value"}],
                },
            ],
            [{"Key": "tag-key", "Value": "match-value"}],
            set(),
        ),
        (
            [
                {
                    "ResourceARN": "ARN1",
                    "Tags": [{"Key": "tag-key", "Value": "no-match-value"}],
                },
                {
                    "ResourceARN": "ARN2",
                    "Tags": [
                        {"Key": "tag-key2", "Value": "match-value2"},
                        {"Key": "tag-key", "Value": "match-value"},
                    ],
                },
            ],
            [
                {"Key": "tag-key", "Value": "match-value"},
                {"Key": "tag-key2", "Value": "match-value2"},
            ],
            {"ARN2"},
        ),
        (
            [
                {
                    "ResourceARN": "ARN1",
                    "Tags": [{"Key": "tag-key", "Value": "match-value"}],
                },
                {
                    "ResourceARN": "ARN2",
                    "Tags": [
                        {"Key": "tag-key2", "Value": "match-value2"},
                        {"Key": "tag-key", "Value": "match-value"},
                    ],
                },
            ],
            [
                {"Key": "tag-key", "Value": "match-value"},
                {"Key": "tag-key2", "Value": "match-value2"},
            ],
            {"ARN1", "ARN2"},
        ),
        (
            [
                {
                    "ResourceARN": "ARN1",
                    "Tags": [{"Key": "tag-key", "Value": ""}],
                },
            ],
            [
                {"Key": "tag-key", "Value": "match-value"},
            ],
            set(),
        ),
        (
            [
                {
                    "ResourceARN": "ARN1",
                    "Tags": [],
                },
            ],
            [
                {"Key": "tag-key", "Value": "match-value"},
            ],
            set(),
        ),
        (
            [
                {
                    "ResourceARN": "ARN1",
                    "Tags": [],
                },
            ],
            [],
            set(),
        ),
        (
            [
                {
                    "ResourceARN": "ARN1",
                    "Tags": [{"Key": "tag-key", "Value": ""}],
                },
            ],
            [],
            set(),
        ),
    ],
)
def test_fetch_resources_matching_tags(fetched_data, tags_to_match, expected_result) -> None:
    with patch("cmk.special_agents.agent_aws._fetch_tagged_resources_with_types") as fetch_fn:
        fetch_fn.return_value = fetched_data
        assert (
            fetch_resources_matching_tags(MagicMock(), tags_to_match, MagicMock())
            == expected_result
        )
