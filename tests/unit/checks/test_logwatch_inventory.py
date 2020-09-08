#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List
import pytest  # type: ignore[import]

from checktestlib import DiscoveryResult, MockHostExtraConf, assertDiscoveryResultsEqual

pytestmark = pytest.mark.checks

INFO1 = [
    ['NODE1', '[[[log1]]]'],
    ['NODE1', '[[[log2]]]'],
    ['NODE1', '[[[log3:missing]]]'],
    ['NODE1', '[[[log4:cannotopen]]]'],
    ['NODE1', '[[[log5]]]'],
    ['NODE2', '[[[log1:missing]]]'],
]

_DEFAULT_PARAMS: Dict[str, List] = {}


@pytest.mark.parametrize('info, fwd_rule, inventory_groups, expected_result', [
    (INFO1, {}, {}, [('log1', _DEFAULT_PARAMS), ('log2', _DEFAULT_PARAMS),
                     ('log5', _DEFAULT_PARAMS)]),
    (INFO1, [{
        'foo': 'bar'
    }], {}, []),
    (INFO1, [{
        'restrict_logfiles': [u'.*2']
    }], {}, [('log1', _DEFAULT_PARAMS), ('log5', _DEFAULT_PARAMS)]),
    (INFO1, [{}], [[('my_group', ('~log.*', '~.*1'))]], [('log1', _DEFAULT_PARAMS)]),
])
def test_logwatch_inventory_single(check_manager, info, fwd_rule, inventory_groups,
                                   expected_result):
    check = check_manager.get_check('logwatch')

    parsed = check.run_parse(info)

    mock_cfgs = [fwd_rule, inventory_groups]

    def mock_cfg(_hostname, _ruleset):
        return mock_cfgs.pop(0)

    with MockHostExtraConf(check, mock_cfg):
        actual_result = DiscoveryResult(check.run_discovery(parsed))
        assertDiscoveryResultsEqual(check, actual_result, DiscoveryResult(expected_result))


@pytest.mark.parametrize(
    'info, fwd_rule, inventory_groups, expected_result',
    [
        (INFO1, {}, {}, []),
        (INFO1, [{
            'foo': 'bar'
        }], {}, []),
        (INFO1, [{}], [[('my_%s_group', ('~(log)[^5]', '~.*1')),
                        ('my_%s_group', ('~(log).*', '~.*5'))]], [
                            ('my_log_group', {
                                'group_patterns': [('~log.*', '~.*5'), ('~log[^5]', '~.*1')],
                            }),
                        ]),
        (INFO1, [{}], [[('my_group', ('~.*sing', '~.*1'))]], []),  # don't match :missing!
    ])
def test_logwatch_inventory_group(check_manager, info, fwd_rule, inventory_groups, expected_result):
    parsed = check_manager.get_check('logwatch').run_parse(info)

    check = check_manager.get_check('logwatch.groups')

    mock_cfgs = [fwd_rule, inventory_groups]

    def mock_cfg(_hostname, _ruleset):
        return mock_cfgs.pop(0)

    with MockHostExtraConf(check, mock_cfg):
        actual_result = DiscoveryResult(check.run_discovery(parsed))
        assertDiscoveryResultsEqual(check, actual_result, DiscoveryResult(expected_result))
