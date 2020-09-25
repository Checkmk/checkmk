#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Dict, List

import pytest  # type: ignore[import]

import cmk.base.config
from cmk.base.plugins.agent_based import logwatch

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State as state
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import Parameters

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('group_patterns, filename, expected', [
    ([], 'lumberjacks.log', {}),
    ([('plain_group', ('*jack*', ''))], 'lumberjacks.log', {
        'plain_group': {('*jack*', '')},
    }),
    ([('plain_group', ('*jack*', '*.log'))], 'lumberjacks.log', {}),
    ([('plain_group', (u'~.*\\..*', ''))], 'lumberjacks.log', {
        'plain_group': {(u'~.*\\..*', '')}
    }),
    ([('%s_group', ('~.{6}(.ack)', ''))], 'lumberjacks.log', {
        'jack_group': {('~.{6}jack', '')},
    }),
    ([('%s', ('~(.).*', '')), ('%s', ('~lumberjacks.([l])og', ''))], 'lumberjacks.log', {
        'l': {('~l.*', ''), ('~lumberjacks.log', '')},
    }),
    ([('%s%s', ('~lum(ber).{8}(.)', '~ladida'))], 'lumberjacks.log', {
        'berg': {('~lumber.{8}g', '~ladida')},
    }),
])
def test_logwatch_groups_of_logfile(group_patterns, filename, expected):
    actual = logwatch._groups_of_logfile(group_patterns, filename)
    assert actual == expected


@pytest.mark.parametrize('group_patterns, filename', [
    ([('%s_group', ('~.{6}.ack', ''))], 'lumberjacks.log'),
])
def test_logwatch_groups_of_logfile_exception(group_patterns, filename):
    with pytest.raises(RuntimeError):
        logwatch._groups_of_logfile(group_patterns, filename)


SECTION1: logwatch.logwatch.Section = {
    'errors': [],
    'logfiles': {
        'mylog': {
            'attr': 'ok',
            'lines': ['C whoha! Someone mooped!'],
        },
        'missinglog': {
            'attr': 'missing',
            'lines': [],
        },
        'unreadablelog': {
            'attr': 'cannotopen',
            'lines': [],
        },
        'empty.log': {
            'attr': 'ok',
            'lines': [],
        },
        'my_other_log': {
            'attr': 'ok',
            'lines': ['W watch your step!'],
        },
    },
}


def test_discovery_single(monkeypatch):
    monkeypatch.setattr(logwatch, '_get_discovery_groups', lambda: [])
    assert sorted(
        logwatch.discover_logwatch_single([], SECTION1),
        key=lambda s: s.item,
    ) == [
        Service(item='empty.log'),
        Service(item='my_other_log'),
        Service(item='mylog'),
    ]

    assert not list(logwatch.discover_logwatch_groups([], SECTION1))


def test_check_single(monkeypatch):
    monkeypatch.setattr(logwatch, 'get_value_store', lambda: {})
    monkeypatch.setattr(logwatch, '_compile_params', lambda: [])
    monkeypatch.setattr(logwatch, 'host_name', lambda: "test-host")
    assert list(logwatch.check_logwatch_node('empty.log', SECTION1)) == [
        Result(
            state=state.OK,
            summary="No error messages",
        ),
    ]
    assert list(logwatch.check_logwatch_node('my_other_log', SECTION1)) == [
        Result(
            state=state.WARN,
            summary='1 WARN messages (Last worst: "watch your step!")',
        ),
    ]
    assert list(logwatch.check_logwatch_node('mylog', SECTION1)) == [
        Result(
            state=state.CRIT,
            summary='1 CRIT messages (Last worst: "whoha! Someone mooped!")',
        ),
    ]


SECTION2: logwatch.logwatch.Section = {
    'errors': [],
    'logfiles': {
        'log1': {
            'attr': 'ok',
            'lines': [],
        },
        'log2': {
            'attr': 'ok',
            'lines': [],
        },
        'log3': {
            'attr': 'missing',
            'lines': [],
        },
        'log4': {
            'attr': 'cannotopen',
            'lines': [],
        },
        'log5': {
            'attr': 'ok',
            'lines': [],
        },
    },
}


def test_logwatch_discover_single_restrict(monkeypatch):
    monkeypatch.setattr(logwatch, '_get_discovery_groups', lambda: [])
    assert sorted(
        logwatch.discover_logwatch_single([Parameters({'restrict_logfiles': [u'.*2']})], SECTION2),
        key=lambda s: s.item,
    ) == [
        Service(item='log1'),
        Service(item='log5'),
    ]


def test_logwatch_discover_single_groups(monkeypatch):
    monkeypatch.setattr(
        logwatch,
        '_get_discovery_groups',
        lambda: [[('my_group', ('~log.*', '~.*1'))]],
    )

    assert list(logwatch.discover_logwatch_single([], SECTION2)) == [
        Service(item='log1'),
    ]


def test_logwatch_discover_groups(monkeypatch):
    monkeypatch.setattr(
        logwatch,
        '_get_discovery_groups',
        lambda: [[
            ('my_%s_group', ('~(log)[^5]', '~.*1')),
            ('my_%s_group', ('~(log).*', '~.*5')),
        ]],
    )

    assert list(logwatch.discover_logwatch_groups([], SECTION2)) == [
        Service(
            item='my_log_group',
            parameters={
                'group_patterns': [
                    ('~log.*', '~.*5'),
                    ('~log[^5]', '~.*1'),
                ],
            },
        ),
    ]
