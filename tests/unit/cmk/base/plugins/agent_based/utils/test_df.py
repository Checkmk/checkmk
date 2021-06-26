#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.base.plugins.agent_based.utils import df


@pytest.mark.parametrize("params,expected", [
    (
        [],
        [('SUMMARY', {}), ('ceph_bar', {}), ('ceph_foo', {})],
    ),
    (
        [[{
            'group_name': 'Foo',
            'patterns_exclude': ['SUMM'],
            'patterns_include': ['ceph*']
        }]],
        [('SUMMARY', {}), ('Foo', {
            'patterns': (['ceph*'], ['SUMM'])
        })],
    ),
])
def test_df_discovery(params, expected):
    actual = df.df_discovery(params, ['SUMMARY', 'ceph_foo', 'ceph_bar'])

    assert len(actual) == len(expected)
    for elem in expected:
        assert elem in actual
