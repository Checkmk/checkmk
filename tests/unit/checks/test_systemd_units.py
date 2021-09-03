#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

import pytest

from tests.testlib import Check

from .checktestlib import MockHostExtraConf

pytestmark = pytest.mark.checks


class UnitEntry(NamedTuple):
    name: str
    type: str
    load: str
    active: str
    sub: str
    description: str
    state: str


@pytest.mark.parametrize('services, blacklist, expected', [
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
        UnitEntry(name=u'alsa-state',
                  type='service',
                  load=u'loaded',
                  active=u'inactive',
                  sub=u'dead',
                  description=u'Manage Sound Card State (restore and store)',
                  state=u'disabled'),
    ], [], {
        "included": [
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
                      state=u'enabled')
        ],
        "excluded": [],
        "disabled": [
            UnitEntry(name=u'alsa-state',
                      type='service',
                      load=u'loaded',
                      active=u'inactive',
                      sub=u'dead',
                      description=u'Manage Sound Card State (restore and store)',
                      state=u'disabled')
        ],
        "static": [],
        "activating": [],
        "reloading": [],
    }),
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
        {
            "included": [
                UnitEntry(name=u'rsyslog',
                          type='service',
                          load=u'loaded',
                          active=u'active',
                          sub=u'running',
                          description=u'System Logging Service',
                          state=u'enabled'),
            ],
            "excluded": [
                UnitEntry(name=u'gpu-manager',
                          type='service',
                          load=u'loaded',
                          active=u'inactive',
                          sub=u'dead',
                          description=u'Detect the available GPUs and deal with any system changes',
                          state=u'unknown'),
            ],
            "disabled": [
                UnitEntry(name=u'alsa-state',
                          type='service',
                          load=u'loaded',
                          active=u'inactive',
                          sub=u'dead',
                          description=u'Manage Sound Card State (restore and store)',
                          state=u'indirect')
            ],
            "static": [],
            "activating": [],
            "reloading": [],
        },
    ),
])
def test_services_split(services, blacklist, expected):
    check = Check('systemd_units')
    services_split = check.context['_services_split']
    actual = services_split(services, blacklist)
    assert actual == expected


@pytest.mark.parametrize(
    'string_table, section',
    [
        (
            [
                ['[list-unit-files]'],
                ['[all]'],
                ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
                [
                    'virtualbox.service',
                    'loaded',
                    'active',
                    'exited',
                    'LSB:',
                    'VirtualBox',
                    'Linux',
                    'kernel',
                    'module',
                ],
            ],
            {
                'service': {
                    'virtualbox': UnitEntry(name='virtualbox',
                                            type='service',
                                            load='loaded',
                                            active='active',
                                            sub='exited',
                                            description='LSB: VirtualBox Linux kernel module',
                                            state='unknown')
                },
            },
        ),
        (
            [
                ['[list-unit-files]'],
                ['[all]'],
                ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
                [
                    'dev-disk-by\\x2did-ata\\x2dAPPLE_SSD_SM0256G_S29CNYDG865465.device',
                    'loaded',
                    'active',
                    'plugged',
                    'APPLE_SSD_SM0256G',
                ],
            ],
            {
                'device': {
                    'dev-disk-by\\x2did-ata\\x2dAPPLE_SSD_SM0256G_S29CNYDG865465': UnitEntry(
                        name='dev-disk-by\\x2did-ata\\x2dAPPLE_SSD_SM0256G_S29CNYDG865465',
                        type='device',
                        load='loaded',
                        active='active',
                        sub='plugged',
                        description='APPLE_SSD_SM0256G',
                        state='unknown')
                },
            },
        ),
        (
            [
                ['[list-unit-files]'],
                ['[all]'],
                ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
                [
                    'cups.path',
                    'loaded',
                    'active',
                    'running',
                    'CUPS',
                    'Scheduler',
                ],
            ],
            {
                'path': {
                    'cups': UnitEntry(name='cups',
                                      type='path',
                                      load='loaded',
                                      active='active',
                                      sub='running',
                                      description='CUPS Scheduler',
                                      state='unknown')
                },
            },
        ),
        (
            [
                ['[list-unit-files]'],
                ['[all]'],
                ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
                [
                    'init.scope',
                    'loaded',
                    'active',
                    'running',
                    'System',
                    'and',
                    'Service',
                    'Manager',
                ],
            ],
            {
                'scope': {
                    'init': UnitEntry(name='init',
                                      type='scope',
                                      load='loaded',
                                      active='active',
                                      sub='running',
                                      description='System and Service Manager',
                                      state='unknown')
                },
            },
        ),
        (
            [
                ['[list-unit-files]'],
                ['[all]'],
                ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
                [
                    'system-getty.slice',
                    'loaded',
                    'active',
                    'active',
                    'system-getty.slice',
                ],
            ],
            {
                'slice': {
                    'system-getty': UnitEntry(name='system-getty',
                                              type='slice',
                                              load='loaded',
                                              active='active',
                                              sub='active',
                                              description='system-getty.slice',
                                              state='unknown')
                },
            },
        ),
        (
            [
                ['[list-unit-files]'],
                ['[all]'],
                ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
                [
                    'systemd-journald.socket',
                    'loaded',
                    'active',
                    'running',
                    'Journal',
                    'Socket',
                ],
            ],
            {
                'socket': {
                    'systemd-journald': UnitEntry(name='systemd-journald',
                                                  type='socket',
                                                  load='loaded',
                                                  active='active',
                                                  sub='running',
                                                  description='Journal Socket',
                                                  state='unknown')
                },
            },
        ),
        (
            [
                ['[list-unit-files]'],
                ['[all]'],
                ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
                [
                    'swapfile.swap',
                    'loaded',
                    'failed',
                    'failed',
                    '/swapfile',
                ],
            ],
            {
                'swap': {
                    'swapfile': UnitEntry(name='swapfile',
                                          type='swap',
                                          load='loaded',
                                          active='failed',
                                          sub='failed',
                                          description='/swapfile',
                                          state='unknown')
                },
            },
        ),
        (
            [
                ['[list-unit-files]'],
                ['[all]'],
                ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
                [
                    'apt-daily-upgrade.timer',
                    'loaded',
                    'active',
                    'waiting',
                    'Daily',
                    'apt',
                    'upgrade',
                    'and',
                    'clean',
                    'activities',
                ],
            ],
            {
                'timer': {
                    'apt-daily-upgrade': UnitEntry(
                        name='apt-daily-upgrade',
                        type='timer',
                        load='loaded',
                        active='active',
                        sub='waiting',
                        description='Daily apt upgrade and clean activities',
                        state='unknown')
                },
            },
        ),
        (
            [
                ['[list-unit-files]'],
                ['[all]'],
                ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
                [
                    'proc-sys-fs-.service.binfmt_misc.automount',  # <- nasty ".service."!
                    'loaded',
                    'active',
                    'running',
                    'Arbitrary',
                    'Executable',
                    'File',
                    'Formats',
                    'File',
                    'System',
                    'Automount',
                    'Point',
                ],
            ],
            {
                'automount': {
                    'proc-sys-fs-.service.binfmt_misc': UnitEntry(
                        name='proc-sys-fs-.service.binfmt_misc',
                        type='automount',
                        load='loaded',
                        active='active',
                        sub='running',
                        description='Arbitrary Executable File Formats File System Automount Point',
                        state='unknown')
                },
            },
        ),
        (
            [
                ['[list-unit-files]'],
                ['[all]'],
                ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
                [
                    'foo.service',
                    'loaded',
                    'failed',
                    'failed',
                    'Arbitrary',
                    'Executable',
                    'File',
                    'Formats',
                    'File',
                    'System',
                    'Automount',
                    'Point',
                ],
                [
                    'bar.service',
                    'loaded',
                    'failed',
                    'failed',
                    'a',
                    'bar',
                    'service',
                ],
            ],
            {
                'service': {
                    'bar': UnitEntry(name='bar',
                                     type='service',
                                     load='loaded',
                                     active='failed',
                                     sub='failed',
                                     description='a bar service',
                                     state='unknown'),
                    'foo': UnitEntry(
                        name='foo',
                        type='service',
                        load='loaded',
                        active='failed',
                        sub='failed',
                        description='Arbitrary Executable File Formats File System Automount Point',
                        state='unknown')
                },
            },
        ),
    ])
def test_parse_systemd_units(string_table, section):
    check = Check('systemd_units')
    assert check.run_parse(string_table) == section


SECTION = {
    'service': {
        'virtualbox': UnitEntry(name='virtualbox',
                                type='service',
                                load='loaded',
                                active='active',
                                sub='exited',
                                description='LSB: VirtualBox Linux kernel module',
                                state='unknown'),
        'bar': UnitEntry(name='bar',
                         type='service',
                         load='loaded',
                         active='failed',
                         sub='failed',
                         description='a bar service',
                         state='unknown'),
        'foo': UnitEntry(
            name='foo',
            type='service',
            load='loaded',
            active='failed',
            sub='failed',
            description='Arbitrary Executable File Formats File System Automount Point',
            state='unknown')
    },
    'device': {
        'dev-disk-by\\x2did-ata\\x2dAPPLE_SSD_SM0256G_S29CNYDG865465': UnitEntry(
            name='dev-disk-by\\x2did-ata\\x2dAPPLE_SSD_SM0256G_S29CNYDG865465',
            type='device',
            load='loaded',
            active='active',
            sub='plugged',
            description='APPLE_SSD_SM0256G',
            state='unknown')
    },
    'path': {
        'cups': UnitEntry(name='cups',
                          type='path',
                          load='loaded',
                          active='active',
                          sub='running',
                          description='CUPS Scheduler',
                          state='unknown')
    },
    'scope': {
        'init': UnitEntry(name='init',
                          type='scope',
                          load='loaded',
                          active='active',
                          sub='running',
                          description='System and Service Manager',
                          state='unknown')
    },
    'slice': {
        'system-getty': UnitEntry(name='system-getty',
                                  type='slice',
                                  load='loaded',
                                  active='active',
                                  sub='active',
                                  description='system-getty.slice',
                                  state='unknown')
    },
    'socket': {
        'systemd-journald': UnitEntry(name='systemd-journald',
                                      type='socket',
                                      load='loaded',
                                      active='active',
                                      sub='running',
                                      description='Journal Socket',
                                      state='unknown')
    },
    'swap': {
        'swapfile': UnitEntry(name='swapfile',
                              type='swap',
                              load='loaded',
                              active='failed',
                              sub='failed',
                              description='/swapfile',
                              state='unknown')
    },
    'timer': {
        'apt-daily-upgrade': UnitEntry(name='apt-daily-upgrade',
                                       type='timer',
                                       load='loaded',
                                       active='active',
                                       sub='waiting',
                                       description='Daily apt upgrade and clean activities',
                                       state='unknown')
    },
    'automount': {
        'proc-sys-fs-.service.binfmt_misc': UnitEntry(
            name='proc-sys-fs-.service.binfmt_misc',
            type='automount',
            load='loaded',
            active='active',
            sub='running',
            description='Arbitrary Executable File Formats File System Automount Point',
            state='unknown')
    },
}


@pytest.mark.parametrize('section, discovery_params, discovered_services', [
    (
        SECTION,
        [
            {
                "names": ["~virtualbox.*"]
            },
        ],
        [('virtualbox', {})],
    ),
    (
        SECTION,
        [],
        [],
    ),
    (
        {},
        [
            {
                "names": ["~virtualbox.*"]
            },
        ],
        [],
    ),
    (
        SECTION,
        [
            {
                "names": ["~aardvark.*"]
            },
        ],
        [],
    ),
])
def test_discover_systemd_units_services(section, discovery_params, discovered_services):
    check = Check('systemd_units.services')

    def mocked_host_conf(_hostname, ruleset):
        if ruleset is check.context.get('discovery_systemd_units_services_rules'):
            return discovery_params
        raise AssertionError('Unknown ruleset in mock host_extra_conf')

    with MockHostExtraConf(check, mocked_host_conf, 'host_extra_conf'):
        assert list(check.run_discovery(section)) == discovered_services


@pytest.mark.parametrize('section, discovered_services', [
    (
        SECTION,
        [('Summary', {})],
    ),
    (
        {},
        [],
    ),
])
def test_discover_systemd_units_services_summary(section, discovered_services):
    check = Check('systemd_units.services_summary')
    assert list(check.run_discovery(section)) == discovered_services
