#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.special_agents.agent_siemens_plc import (
    _addresses_from_device,
    _area_name_to_area_id,
    _cast_values,
    parse_spec,
)


@pytest.mark.parametrize('hostspec, expected_parsed_device', [
    (
        '4fcm;10.2.90.20;0;2;102;merker,5.3,bit,flag,Filterturm_Sammelstoerung_Telefon',
        {
            'host_name': '4fcm',
            'host_address': '10.2.90.20',
            'rack': 0,
            'slot': 2,
            'port': 102,
            'values': [(
                ('merker', None),
                (5, 3),
                'bit',
                'flag',
                'Filterturm_Sammelstoerung_Telefon',
            )],
        },
    ),
    (
        'a885-sps2;10.2.90.131;0;2;102;merker,5.0,bit,None,""',
        {
            'host_name': 'a885-sps2',
            'host_address': '10.2.90.131',
            'rack': 0,
            'slot': 2,
            'port': 102,
            'values': [(
                ('merker', None),
                (5, 0),
                'bit',
                'None',
                '""',
            )],
        },
    ),
    (
        ('ut020;10.2.90.60;0;0;102;merker,5.0,bit,flag,"Kuehlanlage1_Sammelstoerung_Telefon"'
         ';merker,5.1,bit,flag,"Kuehlanlage1_Sammelstoerung_Email"'),
        {
            'host_name': 'ut020',
            'host_address': '10.2.90.60',
            'rack': 0,
            'slot': 0,
            'port': 102,
            'values': [
                (
                    ('merker', None),
                    (5, 0),
                    'bit',
                    'flag',
                    '"Kuehlanlage1_Sammelstoerung_Telefon"',
                ),
                (
                    ('merker', None),
                    (5, 1),
                    'bit',
                    'flag',
                    '"Kuehlanlage1_Sammelstoerung_Email"',
                ),
            ],
        },
    ),
])
def test_parse_spec(hostspec, expected_parsed_device):
    assert parse_spec(hostspec) == expected_parsed_device


@pytest.mark.parametrize('area_name, expected_id', [
    ('merker', 131),
])
def test__area_name_to_area_id(area_name, expected_id):
    assert _area_name_to_area_id(area_name) == expected_id


@pytest.mark.parametrize('device, expected_addresses', [
    (
        {
            'host_name': '4fcm',
            'host_address': '10.2.90.20',
            'rack': 0,
            'slot': 2,
            'port': 102,
            'values': [(
                ('merker', None),
                (5, 3),
                'bit',
                'flag',
                'Filterturm_Sammelstoerung_Telefon',
            )]
        },
        {
            ('merker', None): [5, 6]
        },
    ),
    (
        {
            'host_name': 'a885-sps2',
            'host_address': '10.2.90.131',
            'rack': 0,
            'slot': 2,
            'port': 102,
            'values': [(
                ('merker', None),
                (5, 0),
                'bit',
                'None',
                '""',
            )]
        },
        {
            ('merker', None): [5, 6]
        },
    ),
])
def test__addresses_from_device(device, expected_addresses):
    assert _addresses_from_device(device) == expected_addresses


@pytest.mark.parametrize('device, addresses, data, expected_value', [
    (
        {
            'host_name': '4fcm',
            'host_address': '10.2.90.20',
            'rack': 0,
            'slot': 2,
            'port': 102,
            'values': [(
                ('merker', None),
                (5, 3),
                'bit',
                'flag',
                'Filterturm_Sammelstoerung_Telefon',
            )]
        },
        {
            ('merker', None): [5, 6]
        },
        {
            ('merker', None): b'\x08'
        },
        [
            ('flag', 'Filterturm_Sammelstoerung_Telefon', True),
        ],
    ),
    (
        {
            'host_name': 'a885-sps2',
            'host_address': '10.2.90.131',
            'rack': 0,
            'slot': 2,
            'port': 102,
            'values': [(
                ('merker', None),
                (5, 0),
                'bit',
                'None',
                '""',
            )]
        },
        {
            ('merker', None): [5, 6]
        },
        {
            ('merker', None): b'\x00'
        },
        [
            ('None', '""', False),
        ],
    ),
])
def test__cast_values(device, addresses, data, expected_value):
    assert _cast_values(device, addresses, data) == expected_value
