#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.gui.plugins.wato.check_parameters.interfaces import _transform_discovery_if_rules


@pytest.mark.parametrize('params, result', [
    (
        {
            'discovery_single': (
                True,
                {
                    'item_appearance': 'index',
                    'pad_portnumbers': True,
                },
            ),
            'matching_conditions': (
                True,
                {},
            ),
        },
        {
            'discovery_single': (
                True,
                {
                    'item_appearance': 'index',
                    'pad_portnumbers': True,
                },
            ),
            'matching_conditions': (
                True,
                {},
            ),
        },
    ),
    (
        {
            'discovery_single': (
                True,
                {
                    'item_appearance': 'alias',
                    'pad_portnumbers': True,
                    'labels': {
                        'single': 'wlp'
                    },
                },
            ),
            "grouping": (
                True,
                {
                    'group_items': [{
                        'group_name': 'wlp_group',
                        'member_appearance': 'index',
                    }],
                    'labels': {
                        'group': 'wlp'
                    },
                },
            ),
            'matching_conditions': (
                False,
                {
                    'porttypes': ['5', '9'],
                    'portstates': ['13'],
                    'admin_states': ['2'],
                    'match_index': ['10.*', '2'],
                    'match_desc': ['wlp'],
                    'match_alias': ['lo'],
                },
            ),
        },
        {
            'discovery_single': (
                True,
                {
                    'item_appearance': 'alias',
                    'pad_portnumbers': True,
                    'labels': {
                        'single': 'wlp'
                    },
                },
            ),
            "grouping": (
                True,
                {
                    'group_items': [{
                        'group_name': 'wlp_group',
                        'member_appearance': 'index',
                    }],
                    'labels': {
                        'group': 'wlp'
                    },
                },
            ),
            'matching_conditions': (
                False,
                {
                    'porttypes': ['5', '9'],
                    'portstates': ['13'],
                    'admin_states': ['2'],
                    'match_index': ['10.*', '2'],
                    'match_desc': ['wlp'],
                    'match_alias': ['lo'],
                },
            ),
        },
    ),
    (
        {
            'pad_portnumbers': False,
            'item_appearance': 'alias',
            'match_desc': ['enxe4b97ab99f99', 'vboxnet0', 'lo'],
            'portstates': ['1', '2', '3'],
            'porttypes': ['6'],
            'match_alias': ['enxe4b97ab99f99', 'vboxnet0', 'lo'],
            'rmon': True,
        },
        {
            'discovery_single': (
                True,
                {
                    'item_appearance': 'alias',
                    'pad_portnumbers': False,
                },
            ),
            'matching_conditions': (
                False,
                {
                    'match_alias': ['enxe4b97ab99f99', 'vboxnet0', 'lo'],
                    'match_desc': ['enxe4b97ab99f99', 'vboxnet0', 'lo'],
                    'portstates': ['1', '2', '3'],
                    'porttypes': ['6'],
                },
            ),
        },
    ),
    (
        {
            'portstates': ['1', '2', '9'],
        },
        {
            'matching_conditions': (
                False,
                {
                    'portstates': ['1', '2'],
                },
            ),
        },
    ),
    (
        {
            'portstates': ['9'],
        },
        {
            'matching_conditions': (
                False,
                {
                    'admin_states': ['2'],
                },
            ),
        },
    ),
])
def test_transform_discovery_if_rules(params, result):
    assert _transform_discovery_if_rules(params) == result
