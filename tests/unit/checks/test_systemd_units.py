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
    unit_type: str
    loaded_status: str
    active_status: str
    current_state: str
    description: str
    enabled_status: str


@pytest.mark.parametrize('services, blacklist, expected', [
    ([
        UnitEntry(name=u'gpu-manager',
                  unit_type='service',
                  loaded_status=u'loaded',
                  active_status=u'inactive',
                  current_state=u'dead',
                  description=u'Detect the available GPUs and deal with any system changes',
                  enabled_status=u'unknown'),
        UnitEntry(name=u'rsyslog',
                  unit_type='service',
                  loaded_status=u'loaded',
                  active_status=u'active',
                  current_state=u'running',
                  description=u'System Logging Service',
                  enabled_status=u'enabled'),
        UnitEntry(name=u'alsa-state',
                  unit_type='service',
                  loaded_status=u'loaded',
                  active_status=u'inactive',
                  current_state=u'dead',
                  description=u'Manage Sound Card State (restore and store)',
                  enabled_status=u'disabled'),
    ], [], {
        "included": [
            UnitEntry(name=u'gpu-manager',
                      unit_type='service',
                      loaded_status=u'loaded',
                      active_status=u'inactive',
                      current_state=u'dead',
                      description=u'Detect the available GPUs and deal with any system changes',
                      enabled_status=u'unknown'),
            UnitEntry(name=u'rsyslog',
                      unit_type='service',
                      loaded_status=u'loaded',
                      active_status=u'active',
                      current_state=u'running',
                      description=u'System Logging Service',
                      enabled_status=u'enabled')
        ],
        "excluded": [],
        "disabled": [
            UnitEntry(name=u'alsa-state',
                      unit_type='service',
                      loaded_status=u'loaded',
                      active_status=u'inactive',
                      current_state=u'dead',
                      description=u'Manage Sound Card State (restore and store)',
                      enabled_status=u'disabled')
        ],
        "static": [],
        "activating": [],
        "reloading": [],
    }),
    (
        [
            UnitEntry(name=u'gpu-manager',
                      unit_type='service',
                      loaded_status=u'loaded',
                      active_status=u'inactive',
                      current_state=u'dead',
                      description=u'Detect the available GPUs and deal with any system changes',
                      enabled_status=u'unknown'),
            UnitEntry(name=u'rsyslog',
                      unit_type='service',
                      loaded_status=u'loaded',
                      active_status=u'active',
                      current_state=u'running',
                      description=u'System Logging Service',
                      enabled_status=u'enabled'),
            UnitEntry(name=u'alsa-state',
                      unit_type='service',
                      loaded_status=u'loaded',
                      active_status=u'inactive',
                      current_state=u'dead',
                      description=u'Manage Sound Card State (restore and store)',
                      enabled_status=u'indirect')
        ],
        [u'gpu'],
        {
            "included": [
                UnitEntry(name=u'rsyslog',
                          unit_type='service',
                          loaded_status=u'loaded',
                          active_status=u'active',
                          current_state=u'running',
                          description=u'System Logging Service',
                          enabled_status=u'enabled'),
            ],
            "excluded": [
                UnitEntry(name=u'gpu-manager',
                          unit_type='service',
                          loaded_status=u'loaded',
                          active_status=u'inactive',
                          current_state=u'dead',
                          description=u'Detect the available GPUs and deal with any system changes',
                          enabled_status=u'unknown'),
            ],
            "disabled": [
                UnitEntry(name=u'alsa-state',
                          unit_type='service',
                          loaded_status=u'loaded',
                          active_status=u'inactive',
                          current_state=u'dead',
                          description=u'Manage Sound Card State (restore and store)',
                          enabled_status=u'indirect')
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


@pytest.mark.parametrize('string_table, section', [
    pytest.param(
        [
            ['[all]'],
            ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
            ['0', 'unit', 'files', 'listed.'],
        ],
        {},
        id='No systemd units returns empty parsed section',
    ),
    pytest.param(
        [],
        {},
        id='Empty agent section returns empty parsed section',
    ),
    pytest.param(
        [
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
            ['1', 'unit', 'files', 'listed.'],
        ],
        {},
        id='Missing "[all]" header in agent section leads to empty parsed section',
    ),
    pytest.param(
        [
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
            ['1', 'unit', 'files', 'listed.'],
        ],
        {
            'service': {
                'virtualbox': UnitEntry(name='virtualbox',
                                        unit_type='service',
                                        loaded_status='loaded',
                                        active_status='active',
                                        current_state='exited',
                                        description='LSB: VirtualBox Linux kernel module',
                                        enabled_status='unknown')
            },
        },
        id='Simple agent section parsed correctly',
    ),
    pytest.param(
        [
            ['[all]'],
            ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
            [
                '*',
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
            ['1', 'unit', 'files', 'listed.'],
        ],
        {
            'service': {
                'virtualbox': UnitEntry(name='virtualbox',
                                        unit_type='service',
                                        loaded_status='loaded',
                                        active_status='active',
                                        current_state='exited',
                                        description='LSB: VirtualBox Linux kernel module',
                                        enabled_status='unknown')
            },
        },
        id='Leading "*" in systemd status line is ignored',
    ),
    pytest.param(
        [
            ['[all]'],
            ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
            [
                'active',
                'plugged',
                '',
            ],
            ['1', 'unit', 'files', 'listed.'],
        ],
        {},
        id='Invalid systemd status lines are skipped',
    ),
    pytest.param(
        [
            ['[all]'],
            ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
            [
                'dev-disk-by@did-ata@dAPPLE_SSD_SM0256G_S29CNYDG865465.device.device',
                'loaded',
                'active',
                'plugged',
                'APPLE_SSD_SM0256G',
            ],
            ['1', 'unit', 'files', 'listed.'],
        ],
        {
            'device': {
                'dev-disk-by@did-ata@dAPPLE_SSD_SM0256G_S29CNYDG865465.device': UnitEntry(
                    name='dev-disk-by@did-ata@dAPPLE_SSD_SM0256G_S29CNYDG865465.device',
                    unit_type='device',
                    loaded_status='loaded',
                    active_status='active',
                    current_state='plugged',
                    description='APPLE_SSD_SM0256G',
                    enabled_status='unknown')
            },
        },
        id='Unit type and name parsed correctly from full name',
    ),
    pytest.param(
        [
            ['[list-unit-files]'],
            ['UNIT', 'FILE', 'STATE'],
            ['virtualbox.service', 'enabled'],
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
            ['1', 'unit', 'files', 'listed.'],
        ],
        {
            'service': {
                'virtualbox': UnitEntry(name='virtualbox',
                                        unit_type='service',
                                        loaded_status='loaded',
                                        active_status='active',
                                        current_state='exited',
                                        description='LSB: VirtualBox Linux kernel module',
                                        enabled_status='enabled')
            },
        },
        id='Systemd unit status found in list-unit-files mapping',
    ),
    pytest.param(
        [
            ['[list-unit-files]'],
            ['UNIT', 'FILE', 'STATE'],
            ['someother.service', 'enabled'],
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
            ['1', 'unit', 'files', 'listed.'],
        ],
        {
            'service': {
                'virtualbox': UnitEntry(name='virtualbox',
                                        unit_type='service',
                                        loaded_status='loaded',
                                        active_status='active',
                                        current_state='exited',
                                        description='LSB: VirtualBox Linux kernel module',
                                        enabled_status='unknown')
            },
        },
        id='Systemd unit status not available in list-unit-files mapping, use "unknown" instead',
    ),
    pytest.param(
        [
            ['[list-unit-files]'],
            ['UNIT', 'FILE', 'STATE'],
            ['dev-disk-by@.device', 'enabled'],
            ['[all]'],
            ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
            [
                'dev-disk-by@APPLE_SSD_SM0256G_S29CNYDG865465.device',
                'loaded',
                'active',
                'plugged',
                'APPLE_SSD_SM0256G',
            ],
            ['1', 'unit', 'files', 'listed.'],
        ],
        {
            'device': {
                'dev-disk-by@APPLE_SSD_SM0256G_S29CNYDG865465': UnitEntry(
                    name='dev-disk-by@APPLE_SSD_SM0256G_S29CNYDG865465',
                    unit_type='device',
                    loaded_status='loaded',
                    active_status='active',
                    current_state='plugged',
                    description='APPLE_SSD_SM0256G',
                    enabled_status='enabled')
            },
        },
        id='Unit status found in list-unit-files mapping even though unit names are diverging',
    ),
])
def test_parse_systemd_units(string_table, section):
    check = Check('systemd_units')
    assert check.run_parse(string_table) == section


SECTION = {
    'service': {
        'virtualbox': UnitEntry(name='virtualbox',
                                unit_type='service',
                                loaded_status='loaded',
                                active_status='active',
                                current_state='exited',
                                description='LSB: VirtualBox Linux kernel module',
                                enabled_status='unknown'),
        'bar': UnitEntry(name='bar',
                         unit_type='service',
                         loaded_status='loaded',
                         active_status='failed',
                         current_state='failed',
                         description='a bar service',
                         enabled_status='unknown'),
        'foo': UnitEntry(
            name='foo',
            unit_type='service',
            loaded_status='loaded',
            active_status='failed',
            current_state='failed',
            description='Arbitrary Executable File Formats File System Automount Point',
            enabled_status='unknown')
    },
    'device': {
        'dev-disk-by\\x2did-ata\\x2dAPPLE_SSD_SM0256G_S29CNYDG865465': UnitEntry(
            name='dev-disk-by\\x2did-ata\\x2dAPPLE_SSD_SM0256G_S29CNYDG865465',
            unit_type='device',
            loaded_status='loaded',
            active_status='active',
            current_state='plugged',
            description='APPLE_SSD_SM0256G',
            enabled_status='unknown')
    },
    'path': {
        'cups': UnitEntry(name='cups',
                          unit_type='path',
                          loaded_status='loaded',
                          active_status='active',
                          current_state='running',
                          description='CUPS Scheduler',
                          enabled_status='unknown')
    },
    'scope': {
        'init': UnitEntry(name='init',
                          unit_type='scope',
                          loaded_status='loaded',
                          active_status='active',
                          current_state='running',
                          description='System and Service Manager',
                          enabled_status='unknown')
    },
    'slice': {
        'system-getty': UnitEntry(name='system-getty',
                                  unit_type='slice',
                                  loaded_status='loaded',
                                  active_status='active',
                                  current_state='active',
                                  description='system-getty.slice',
                                  enabled_status='unknown')
    },
    'socket': {
        'systemd-journald': UnitEntry(name='systemd-journald',
                                      unit_type='socket',
                                      loaded_status='loaded',
                                      active_status='active',
                                      current_state='running',
                                      description='Journal Socket',
                                      enabled_status='unknown')
    },
    'swap': {
        'swapfile': UnitEntry(name='swapfile',
                              unit_type='swap',
                              loaded_status='loaded',
                              active_status='failed',
                              current_state='failed',
                              description='/swapfile',
                              enabled_status='unknown')
    },
    'timer': {
        'apt-daily-upgrade': UnitEntry(name='apt-daily-upgrade',
                                       unit_type='timer',
                                       loaded_status='loaded',
                                       active_status='active',
                                       current_state='waiting',
                                       description='Daily apt upgrade and clean activities',
                                       enabled_status='unknown')
    },
    'automount': {
        'proc-sys-fs-.service.binfmt_misc': UnitEntry(
            name='proc-sys-fs-.service.binfmt_misc',
            unit_type='automount',
            loaded_status='loaded',
            active_status='active',
            current_state='running',
            description='Arbitrary Executable File Formats File System Automount Point',
            enabled_status='unknown')
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


@pytest.mark.parametrize('item, params, section, check_results', [
    (
        'virtualbox',
        {
            'else': 2,
            'states': {
                'active': 0,
                'failed': 2,
                'inactive': 0
            },
            'states_default': 2,
        },
        SECTION,
        [
            (0, 'Status: active'),
            (0, 'LSB: VirtualBox Linux kernel module'),
        ],
    ),
    (
        'foo',
        {
            'else': 2,
            'states': {
                'active': 0,
                'failed': 2,
                'inactive': 0
            },
            'states_default': 2,
        },
        SECTION,
        [
            (2, 'Status: failed'),
            (0, 'Arbitrary Executable File Formats File System Automount Point'),
        ],
    ),
    (
        'something',
        {
            'else': 2,
            'states': {
                'active': 0,
                'failed': 2,
                'inactive': 0
            },
            'states_default': 2,
        },
        SECTION,
        [(2, 'Service not found')],
    ),
    (
        'something',
        {
            'else': 2,
            'states': {
                'active': 0,
                'failed': 2,
                'inactive': 0
            },
            'states_default': 2,
        },
        {},
        [(2, 'Service not found')],
    ),
])
def test_check_systemd_units_services(item, params, section, check_results):
    check = Check('systemd_units.services')
    assert list(check.run_check(item, params, section)) == check_results


@pytest.mark.parametrize(
    'params, section, check_results',
    [

        # "Normal" test case
        (
            {
                'else': 2,
                'states': {
                    'active': 0,
                    'failed': 2,
                    'inactive': 0
                },
                'states_default': 2,
            },
            SECTION,
            [
                (0, 'Total: 3'),
                (0, 'Disabled: 0'),
                (0, 'Failed: 2'),
                (2, '2 services failed (bar, foo)'),
            ],
        ),
        # Ignored (see 'blacklist')
        (
            {
                'ignored': 'virtual',
            },
            {
                'service': {
                    'virtualbox': UnitEntry(name='virtualbox',
                                            unit_type='service',
                                            loaded_status='loaded',
                                            active_status='active',
                                            current_state='exited',
                                            description='LSB: VirtualBox Linux kernel module',
                                            enabled_status='unknown'),
                },
            },
            [
                (0, 'Total: 1'),
                (0, 'Disabled: 0'),
                (0, 'Failed: 0'),
                (0, '\nIgnored: 1'),
            ],
        ),
        # Activating
        (
            {},
            {
                'service': {
                    'virtualbox': UnitEntry(name='virtualbox',
                                            unit_type='service',
                                            loaded_status='loaded',
                                            active_status='activating',
                                            current_state='exited',
                                            description='LSB: VirtualBox Linux kernel module',
                                            enabled_status='unknown'),
                },
            },
            [
                (0, 'Total: 1'),
                (0, 'Disabled: 0'),
                (0, 'Failed: 0'),
                (0, "Service 'virtualbox' activating for: 0.00 s", []),
            ],
        ),
        # Activating + reloading
        (
            {},
            {
                'service': {
                    'virtualbox': UnitEntry(name='virtualbox',
                                            unit_type='service',
                                            loaded_status='loaded',
                                            active_status='activating',
                                            current_state='exited',
                                            description='LSB: VirtualBox Linux kernel module',
                                            enabled_status='reloading'),
                },
            },
            [
                (0, 'Total: 1'),
                (0, 'Disabled: 0'),
                (0, 'Failed: 0'),
                (0, "Service 'virtualbox' activating for: 0.00 s", []),
            ],
        ),
        # Reloading
        (
            {},
            {
                'service': {
                    'virtualbox': UnitEntry(name='virtualbox',
                                            unit_type='service',
                                            loaded_status='loaded',
                                            active_status='active',
                                            current_state='exited',
                                            description='LSB: VirtualBox Linux kernel module',
                                            enabled_status='reloading'),
                },
            },
            [
                (0, 'Total: 1'),
                (0, 'Disabled: 0'),
                (0, 'Failed: 0'),
                (0, "Service 'virtualbox' reloading for: 0.00 s", []),
            ],
        ),
        # Indirect
        (
            {},
            {
                'service': {
                    'virtualbox': UnitEntry(name='virtualbox',
                                            unit_type='service',
                                            loaded_status='loaded',
                                            active_status='active',
                                            current_state='exited',
                                            description='LSB: VirtualBox Linux kernel module',
                                            enabled_status='indirect'),
                },
            },
            [
                (0, 'Total: 1'),
                (0, 'Disabled: 1'),
                (0, 'Failed: 0'),
            ],
        ),
        # Custom systemd state
        (
            {
                'else': 2,
                'states': {
                    'active': 0,
                    'failed': 2,
                    'inactive': 0
                },
                'states_default': 2,
            },
            {
                'service': {
                    'virtualbox': UnitEntry(name='virtualbox',
                                            unit_type='service',
                                            loaded_status='loaded',
                                            active_status='somesystemdstate',
                                            current_state='exited',
                                            description='LSB: VirtualBox Linux kernel module',
                                            enabled_status='unknown'),
                },
            },
            [
                (0, 'Total: 1'),
                (0, 'Disabled: 0'),
                (0, 'Failed: 0'),
                (2, '1 service somesystemdstate (virtualbox)'),
            ],
        ),
    ])
def test_check_systemd_units_services_summary(params, section, check_results):
    check = Check('systemd_units.services_summary')
    assert list(check.run_check('', params, section)) == check_results
