#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.utils.df import get_filesystem_levels

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('size_gb, params, expected_levels', [
    (
        2.0,
        {
            'levels': (80.0, 90.0),
        },
        {
            'inodes_levels': (None, None),
            'levels': (80.0, 90.0),
            'levels_low': (50.0, 60.0),
            'levels_mb': (1638.4, 1843.2),
            'levels_text': '(warn/crit at 80.00%/90.00%)',
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24,
        },
    ),
    (
        2.0,
        {
            'levels': (1500, 2000),
        },
        {
            'inodes_levels': (None, None),
            'levels': (1500, 2000),
            'levels_low': (50.0, 60.0),
            'levels_mb': (1500.0, 2000.0),
            'levels_text': '(warn/crit at 1.46 GiB/1.95 GiB)',
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24,
        },
    ),
    (
        2.0,
        {
            'levels': (80.0, 90.0),
            'magic': 0.9,
        },
        {
            'inodes_levels': (None, None),
            'levels': (80.0, 90.0),
            'levels_low': (50.0, 60.0),
            'levels_mb': (1532.344151329109, 1790.1720756645545),
            'levels_text': '(warn/crit at 74.82%/87.41%)',
            'magic': 0.9,
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24,
        },
    ),
    (
        2.0,
        {
            'levels': (1500, 2000),
            'magic': 0.9,
        },
        {
            'inodes_levels': (None, None),
            'levels': (1500, 2000),
            'levels_low': (50.0, 60.0),
            'levels_mb': (1358.1088743367964, 1987.57158023388),
            'levels_text': '(warn/crit at 66.31%/97.05%)',
            'magic': 0.9,
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24,
        },
    ),
])
def test_get_filesystem_levels(size_gb, params, expected_levels):
    levels = get_filesystem_levels(size_gb, params)
    assert levels == expected_levels
