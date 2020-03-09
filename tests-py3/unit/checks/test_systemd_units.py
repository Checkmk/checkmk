#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks

UnitEntry = collections.namedtuple(
    "UnitEntry", ['name', 'type', 'load', 'active', 'sub', 'description', 'state'])


@pytest.mark.parametrize('services, blacklist, expected', [
    (
        [
            UnitEntry(name=u'gpu-manager',
                      type='service',
                      load=u'loaded',
                      active=u'inactive',
                      sub=u'dead',
                      description=u'Detect the available GPUs and deal with any system changes',
                      state=u'unknown'),
            UnitEntry(name=u'rsyslog',
                      type='service',
                      load=u'loaded',
                      active=u'active',
                      sub=u'running',
                      description=u'System Logging Service',
                      state=u'enabled'),
            UnitEntry(name=u'alsa-state',
                      type='service',
                      load=u'loaded',
                      active=u'inactive',
                      sub=u'dead',
                      description=u'Manage Sound Card State (restore and store)',
                      state=u'disabled'),
        ],
        [],
        ([
            UnitEntry(name=u'gpu-manager',
                      type='service',
                      load=u'loaded',
                      active=u'inactive',
                      sub=u'dead',
                      description=u'Detect the available GPUs and deal with any system changes',
                      state=u'unknown'),
            UnitEntry(name=u'rsyslog',
                      type='service',
                      load=u'loaded',
                      active=u'active',
                      sub=u'running',
                      description=u'System Logging Service',
                      state=u'enabled'),
        ], [], [
            UnitEntry(name=u'alsa-state',
                      type='service',
                      load=u'loaded',
                      active=u'inactive',
                      sub=u'dead',
                      description=u'Manage Sound Card State (restore and store)',
                      state=u'disabled'),
        ], [], []),
    ),
    (
        [
            UnitEntry(name=u'gpu-manager',
                      type='service',
                      load=u'loaded',
                      active=u'inactive',
                      sub=u'dead',
                      description=u'Detect the available GPUs and deal with any system changes',
                      state=u'unknown'),
            UnitEntry(name=u'rsyslog',
                      type='service',
                      load=u'loaded',
                      active=u'active',
                      sub=u'running',
                      description=u'System Logging Service',
                      state=u'enabled'),
            UnitEntry(name=u'alsa-state',
                      type='service',
                      load=u'loaded',
                      active=u'inactive',
                      sub=u'dead',
                      description=u'Manage Sound Card State (restore and store)',
                      state=u'indirect')
        ],
        [u'gpu'],
        ([
            UnitEntry(name=u'rsyslog',
                      type='service',
                      load=u'loaded',
                      active=u'active',
                      sub=u'running',
                      description=u'System Logging Service',
                      state=u'enabled'),
        ], [
            UnitEntry(name=u'gpu-manager',
                      type='service',
                      load=u'loaded',
                      active=u'inactive',
                      sub=u'dead',
                      description=u'Detect the available GPUs and deal with any system changes',
                      state=u'unknown'),
        ], [
            UnitEntry(name=u'alsa-state',
                      type='service',
                      load=u'loaded',
                      active=u'inactive',
                      sub=u'dead',
                      description=u'Manage Sound Card State (restore and store)',
                      state=u'indirect')
        ], [], []),
    ),
])
def test_services_split(check_manager, services, blacklist, expected):
    check = check_manager.get_check('systemd_units')
    services_split = check.context['_services_split']
    actual = services_split(services, blacklist)
    assert actual == expected
