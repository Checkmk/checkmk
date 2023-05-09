#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.gui.plugins.wato.datasource_programs import _special_agents_kubernetes_transform, MultisiteBiDatasource


@pytest.mark.parametrize('parameters, expected_result', [
    (
        {
            'url-prefix': 'https://someserver:123/blah',
        },
        {
            'infos': ['nodes'],
            'no-cert-check': False,
            'namespaces': False,
            'api-server-endpoint': (
                'url_custom',
                'https://someserver:123/blah',
            ),
        },
    ),
    (
        {
            'url-prefix': 'https://someserver',
            'port': 123,
            'path-prefix': 'blah',
        },
        {
            'infos': ['nodes'],
            'no-cert-check': False,
            'namespaces': False,
            'api-server-endpoint': (
                'url_custom',
                'https://someserver:123/blah',
            ),
        },
    ),
    (
        {
            'port': 123,
            'path-prefix': 'blah',
        },
        {
            'infos': ['nodes'],
            'no-cert-check': False,
            'namespaces': False,
            'api-server-endpoint': (
                'ipaddress',
                {
                    'port': 123,
                    'path-prefix': 'blah',
                },
            ),
        },
    ),
    (
        {},
        {
            'infos': ['nodes'],
            'no-cert-check': False,
            'namespaces': False,
            'api-server-endpoint': (
                'ipaddress',
                {},
            ),
        },
    ),
])
def test__special_agents_kubernetes_transform(parameters, expected_result):
    assert _special_agents_kubernetes_transform(parameters) == expected_result


@pytest.fixture(scope="function")
def _bi_datasource_parameters():
    # parameter format introduced with 2.0.0p9
    return {
        'site': 'local',
        'credentials': 'automation',
        'filter': {
            'aggr_name': ['Host admin-pc'],
            'aggr_group_prefix': ['Hosts']
        }
    }


@pytest.mark.parametrize(
    "value",
    [
        (
            # filter keys till 2.0.0p8
            {
                'site': 'local',
                'credentials': 'automation',
                'filter': {
                    'aggr_name_regex': ['Host admin-pc'],
                    'aggr_groups': ['Hosts']
                }
            }),
        ({
            # filter keys from 2.0.0p9
            'site': 'local',
            'credentials': 'automation',
            'filter': {
                'aggr_name': ['Host admin-pc'],
                'aggr_group_prefix': ['Hosts']
            }
        })
    ],
)
def test_bi_datasource_parameters(value, _bi_datasource_parameters):
    assert MultisiteBiDatasource().get_valuespec().transform_value(
        value) == _bi_datasource_parameters
