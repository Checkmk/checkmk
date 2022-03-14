#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.utils import df


@pytest.mark.parametrize(
    "params,expected",
    [
        (
            [],
            [("SUMMARY", {}), ("ceph_bar", {}), ("ceph_foo", {})],
        ),
        (
            [
                {
                    "groups": [
                        {
                            "group_name": "Foo",
                            "patterns_exclude": ["SUMM"],
                            "patterns_include": ["ceph*"],
                        }
                    ]
                }
            ],
            [("SUMMARY", {}), ("Foo", {"patterns": (["ceph*"], ["SUMM"])})],
        ),
    ],
)
def test_df_discovery(params, expected):
    actual = df.df_discovery(params, ["SUMMARY", "ceph_foo", "ceph_bar"])

    assert len(actual) == len(expected)
    for elem in expected:
        assert elem in actual


@pytest.mark.parametrize(
    "params,expected",
    [
        (
            ({"fake": "fake"}, "/fake", None, None, None, None, None, {"fake": "fake"}, None),
            (Result(state=State.OK, summary="no filesystem size information"),),
        ),
        (
            ({"fake": "fake"}, "/fake", 0, None, None, None, None, {"fake": "fake"}, None),
            (Result(state=State.WARN, summary="Size of filesystem is 0 MB"),),
        ),
    ],
)
def test_df_check_filesystem_single(params, expected):
    """Check only the early exit Result if size_mb or avail_mb or reserved_mb is None."""
    result = tuple(df.df_check_filesystem_single(*params))

    assert result == expected


@pytest.mark.parametrize(
    "mplist,patterns_include,patterns_exclude,expected",
    [
        (
            {
                "fake1": {
                    "size_mb": None,
                    "avail_mb": None,
                    "reserved_mb": 0,
                },
                "fake2": {
                    "size_mb": None,
                    "avail_mb": None,
                    "reserved_mb": 0,
                },
            },
            ["fake1", "fake2"],
            [],
            ["fake1", "fake2"],
        ),
        (
            {  # pylint:disable= duplicate-key
                "fake_same_name": {
                    "size_mb": None,
                    "avail_mb": None,
                    "reserved_mb": 0,
                },
                "fake_same_name": {
                    "size_mb": None,
                    "avail_mb": None,
                    "reserved_mb": 0,
                },
            },
            ["fake_same_name", "fake_same_name"],
            [],
            ["fake_same_name"],
        ),
    ],
    ids=["unique", "duplicates"],
)
def test_mountpoints_in_group(mplist, patterns_include, patterns_exclude, expected):
    """Returns list of mountpoints without duplicates."""

    result = df.mountpoints_in_group(mplist, patterns_include, patterns_exclude)

    assert isinstance(result, list)
    assert result == expected
