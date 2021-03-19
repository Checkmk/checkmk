#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

_defaults = {'FastSaved': 0,
             'FastSavedCritical': 2,
             'FastSaving': 0,
             'FastSavingCritical': 2,
             'Off': 1,
             'OffCritical': 2,
             'Other': 3,
             'Paused': 0,
             'PausedCritical': 2,
             'Pausing': 0,
             'PausingCritical': 2,
             'Reset': 1,
             'ResetCritical': 2,
             'Resuming': 0,
             'ResumingCritical': 2,
             'Running': 0,
             'RunningCritical': 2,
             'Saved': 0,
             'SavedCritical': 2,
             'Saving': 0,
             'SavingCritical': 2,
             'Starting': 0,
             'StartingCritical': 2,
             'Stopping': 1,
             'StoppingCritical': 2}


checkname = 'hyperv_vms'


info = [['"Name"', '"State"', '"Uptime"', '"Status"'],
        ['Q-WSUS', 'Running', '4.21:44:29', 'Operating normally'],
        ['"AUN-CAA"', '"Off"', '"00:00:00"', '"Operating normally"'],
        ['weg-ca-webserver', 'Wrong', '00:00:00', 'Operating normally'],
        ['z4058044_snap (23.05.2014 - 09:29:29)', 'Running', '18:20:34', 'Operating normally'],
        ['z230897', 'Stopping', '18:20:34', 'VM crashed'],
        ['hlv2', 'UnknownState', '00:00:00', 'Totally normal'],
        ['hlv3', 'Running', '00:00:00', 'Operating normally'],
        ['& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot'],
        ['']]


discovery = {'': [('Q-WSUS', {'state': 'Running'}),
                  ('AUN-CAA', {'state': 'Off'}),
                  ('weg-ca-webserver', {'state': 'Wrong'}),
                  ('z4058044_snap (23.05.2014 - 09:29:29)', {'state': 'Running'}),
                  ('z230897', {'state': 'Stopping'}),
                  ('hlv2', {'state': 'UnknownState'}),
                  ('hlv3', {'state': 'Running'})]}


checks = {'': [('Q-WSUS',
                {'state': 'Running', **_defaults},
                [(0, 'State is Running (Operating normally)')]),
               ('AUN-CAA',
                {'state': 'Off', **_defaults},
                [(1, 'State is Off (Operating normally)')]),
               ('weg-ca-webserver',
                {'state': 'Wrong', **_defaults},
                [(3, 'Unknown state Wrong (Operating normally)')]),
               ('z4058044_snap (23.05.2014 - 09:29:29)',
                {'state': 'Running', **_defaults, 'compare_discovery': True},
                [(0, 'State Running (Operating normally) matches discovery')]),
               ('z230897',
                {'state': 'Running', **_defaults, 'compare_discovery': True},
                [(2, 'State Stopping (VM crashed) does not match discovery (Running)')]),
               ('hlv2',
                {'state': 'UnknownState', **_defaults, 'compare_discovery': True},
                [(0, 'State UnknownState (Totally normal) matches discovery')]),
               ('hlv3',
                {**_defaults, 'compare_discovery': True},
                [(3, 'State is Running (Operating normally), discovery state is not available')])]}
