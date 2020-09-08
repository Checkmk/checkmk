#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List
import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.logwatch_section import parse_logwatch
from cmk.base.plugins.agent_based import logwatch_ec
from cmk.base.plugins.agent_based.agent_based_api.v1 import Service

pytestmark = pytest.mark.checks

INFO1 = [
    ['[[[log1]]]'],
    ['[[[log2]]]'],
    ['[[[log3:missing]]]'],
    ['[[[log4:cannotopen]]]'],
    ['[[[log5]]]'],
    ['[[[log1:missing]]]'],
]


@pytest.mark.parametrize('info, fwd_rule, expected_result', [
    (INFO1, [], []),
    (INFO1, [{
        'separate_checks': True
    }], [
        Service(item='log1', parameters={'expected_logfiles': ['log1']}),
        Service(item='log2', parameters={'expected_logfiles': ['log2']}),
        Service(item='log5', parameters={'expected_logfiles': ['log5']}),
    ]),
    (INFO1, [{
        'restrict_logfiles': [u'.*']
    }], []),
    (INFO1, [{
        'restrict_logfiles': [u'.*'],
        'separate_checks': True,
    }], [
        Service(item='log1', parameters={'expected_logfiles': ['log1']}),
        Service(item='log2', parameters={'expected_logfiles': ['log2']}),
        Service(item='log5', parameters={'expected_logfiles': ['log5']}),
    ]),
    (INFO1, [{
        'restrict_logfiles': [u'.*'],
        'separate_checks': False,
    }], []),
    (INFO1, [{
        'restrict_logfiles': [u'.*'],
    }], []),
    (INFO1, [{
        'restrict_logfiles': [u'log1'],
        'separate_checks': True,
        'method': 'pass me on!',
        'facility': 'pass me on!',
        'monitor_logfilelist': 'pass me on!',
        'logwatch_reclassify': 'pass me on!',
        'some_other_key': 'I should be discarded!',
    }], [
        Service(item='log1',
                parameters={
                    'expected_logfiles': ['log1'],
                    'method': 'pass me on!',
                    'facility': 'pass me on!',
                    'monitor_logfilelist': 'pass me on!',
                    'logwatch_reclassify': 'pass me on!',
                }),
    ]),
])
def test_logwatch_ec_inventory_single(info, fwd_rule, expected_result):
    parsed = parse_logwatch(info)

    actual_result = sorted(logwatch_ec.discover_single(fwd_rule, parsed), key=lambda s: s.item)
    assert actual_result == expected_result


@pytest.mark.parametrize('info, fwd_rule, expected_result', [
    (INFO1, [], []),
    (INFO1, [{
        'separate_checks': True
    }], []),
    (INFO1, [{
        'separate_checks': False
    }], [
        Service(parameters={'expected_logfiles': ['log1', 'log2', 'log5']}),
    ]),
    (INFO1, [{
        'restrict_logfiles': [u'.*[12]'],
        'separate_checks': False
    }], [
        Service(parameters={'expected_logfiles': ['log1', 'log2']}),
    ]),
])
def test_logwatch_ec_inventory_groups(info, fwd_rule, expected_result):
    parsed = parse_logwatch(info)

    actual_result = list(logwatch_ec.discover_group(fwd_rule, parsed))
    assert actual_result == expected_result
