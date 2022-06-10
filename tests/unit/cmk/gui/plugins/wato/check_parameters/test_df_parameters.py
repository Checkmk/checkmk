#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import copy

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.check_parameters.filesystem import (
    _transform_discovery_filesystem_params,
    _transform_filesystem_groups,
    _validate_discovery_filesystem_params,
)
from cmk.gui.plugins.wato.check_parameters.filesystem_utils import (
    _transform_discovered_filesystem_params,
)


@pytest.mark.parametrize(
    "params",
    [
        {
            "item_appearance": "mountpoint",
            "grouping_behaviour": "volume_name_and_mountpoint",
        },
        # 1
        {
            "item_appearance": "uuid_and_mountpoint",
            "grouping_behaviour": "volume_name_and_mountpoint",
        },
        {
            "item_appearance": "volume_name_and_mountpoint",
            "grouping_behaviour": "uuid_and_mountpoint",
        },
        # 2
        {
            "mountpoint_for_block_devices": "uuid_as_mountpoint",
            "item_appearance": "volume_name_and_mountpoint",
        },
        {
            "mountpoint_for_block_devices": "volume_name_as_mountpoint",
            "item_appearance": "uuid_and_mountpoint",
        },
        # 3
        {
            "mountpoint_for_block_devices": "uuid_as_mountpoint",
            "grouping_behaviour": "volume_name_and_mountpoint",
        },
        {
            "mountpoint_for_block_devices": "volume_name_as_mountpoint",
            "grouping_behaviour": "uuid_and_mountpoint",
        },
        # 4
        {
            "mountpoint_for_block_devices": "uuid_as_mountpoint",
            "item_appearance": "volume_name_and_mountpoint",
            "grouping_behaviour": "volume_name_and_mountpoint",
        },
        {
            "mountpoint_for_block_devices": "volume_name_as_mountpoint",
            "item_appearance": "uuid_and_mountpoint",
            "grouping_behaviour": "volume_name_and_mountpoint",
        },
        {
            "mountpoint_for_block_devices": "volume_name_as_mountpoint",
            "item_appearance": "volume_name_and_mountpoint",
            "grouping_behaviour": "uuid_and_mountpoint",
        },
        # 5
        {
            "mountpoint_for_block_devices": "uuid_as_mountpoint",
            "item_appearance": "volume_name_and_mountpoint",
            "grouping_behaviour": "mountpoint",
        },
        {
            "mountpoint_for_block_devices": "volume_name_as_mountpoint",
            "item_appearance": "uuid_and_mountpoint",
            "grouping_behaviour": "mountpoint",
        },
    ],
)
def test_invalid_discovery_df_rules(params):
    with pytest.raises(MKUserError):
        _validate_discovery_filesystem_params(params, "varprefix")


@pytest.mark.parametrize(
    "params, result",
    [
        ({}, {}),
        (
            {
                "include_volume_name": False,
            },
            {
                "item_appearance": "mountpoint",
                "grouping_behaviour": "mountpoint",
            },
        ),
        (
            {
                "include_volume_name": (True, "mountpoint"),
            },
            {
                "item_appearance": "volume_name_and_mountpoint",
                "grouping_behaviour": "mountpoint",
            },
        ),
        (
            {
                "include_volume_name": (True, "volume_name_and_mountpoint"),
            },
            {
                "item_appearance": "volume_name_and_mountpoint",
                "grouping_behaviour": "volume_name_and_mountpoint",
            },
        ),
    ],
)
def test__transform_discovery_filesystem_params(params, result):
    p = copy.deepcopy(params)
    r = _transform_discovery_filesystem_params(params)
    assert r == result
    assert p == params


@pytest.mark.parametrize(
    "params, result",
    [
        ({}, {}),
        (
            {
                "include_volume_name": False,
            },
            {
                "item_appearance": "mountpoint",
            },
        ),
        (
            {
                "include_volume_name": True,
            },
            {
                "item_appearance": "volume_name_and_mountpoint",
            },
        ),
    ],
)
def test__transform_discovered_filesystem_params(params, result):
    assert _transform_discovered_filesystem_params(params) == result


@pytest.mark.parametrize(
    "params, result",
    [
        (
            [
                ("OLD-OLD-group_name", "include_pattern_1"),
                ("OLD-OLD-group_name", "include_pattern_2"),
            ],
            {
                "groups": [
                    {
                        "group_name": "OLD-OLD-group_name",
                        "patterns_include": ["include_pattern_1", "include_pattern_2"],
                        "patterns_exclude": [],
                    }
                ]
            },
        ),
        (
            [
                {
                    "group_name": "OLD",
                    "patterns_include": ["FOO", "BAR"],
                    "patterns_exclude": ["NOT", "INCLUDE"],
                }
            ],
            {
                "groups": [
                    {
                        "group_name": "OLD",
                        "patterns_include": ["FOO", "BAR"],
                        "patterns_exclude": ["NOT", "INCLUDE"],
                    }
                ]
            },
        ),
        (
            {
                "groups": [
                    {
                        "group_name": "NEW",
                        "patterns_include": ["FOO", "BAR"],
                        "patterns_exclude": ["NOT", "INCLUDE"],
                    }
                ]
            },
            {
                "groups": [
                    {
                        "group_name": "NEW",
                        "patterns_include": ["FOO", "BAR"],
                        "patterns_exclude": ["NOT", "INCLUDE"],
                    }
                ]
            },
        ),
    ],
)
def test__transform_filesystem_groups(params, result):
    assert _transform_filesystem_groups(params) == result
