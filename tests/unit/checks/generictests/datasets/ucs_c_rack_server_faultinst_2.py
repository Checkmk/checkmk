#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.ucs_c_rack_server_faultinst import (
    parse_ucs_c_rack_server_faultinst,
)

checkname = 'ucs_c_rack_server_faultinst'

parsed = parse_ucs_c_rack_server_faultinst([
    ['faultInst', 'severity info', 'cause powerproblem', 'code F0883', 'descr Broken',
     'affectedDN sys/rack-unit-1/psu-4'],
    ['faultInst', 'severity condition', 'cause powerproblem', 'code F0883', 'descr Broken',
     'affectedDN sys/rack-unit-1/psu-4'],
    ['faultInst', 'severity cleared', 'cause powerproblem', 'code F0883', 'descr Broken',
     'affectedDN sys/rack-unit-1/psu-4'],
    ['faultInst', 'severity minor', 'cause powerproblem', 'code F0883', 'descr Broken',
     'affectedDN sys/rack-unit-1/psu-4'],
    ['faultInst', 'severity warning', 'cause powerproblem', 'code F0883', 'descr Broken',
     'affectedDN sys/rack-unit-1/psu-4'],
    ['faultInst', 'severity major', 'cause powerproblem', 'code F0883', 'descr Broken',
     'affectedDN sys/rack-unit-1/psu-4'],
    ['faultInst', 'severity critical', 'cause powerproblem', 'code F0883', 'descr Broken',
     'affectedDN sys/rack-unit-1/psu-4'],
    ['faultInst', 'severity unknown', 'cause powerproblem', 'code F0883', 'descr Broken',
     'affectedDN sys/rack-unit-1/psu-4'],
])

discovery = {'': [(None, {})]}

checks = {'': [(None,
                {},
                [(2,
                  "Found faults: 1 with severity 'cleared', 1 with severity 'condition', 1 with "
                  "severity 'critical', 1 with severity 'info', 1 with severity 'major', 1 "
                  "with severity 'minor', 1 with severity 'unknown', 1 with severity 'warning'"),
                 (0,
                  '\n\nIndividual faults:\nSeverity: info, Description: Broken, Cause: '
                  'powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4'),
                 (0,
                  'Severity: condition, Description: Broken, Cause: powerproblem, Code: F0883, '
                  'Affected DN: rack-unit-1/psu-4'),
                 (0,
                  'Severity: cleared, Description: Broken, Cause: powerproblem, Code: F0883, '
                  'Affected DN: rack-unit-1/psu-4'),
                 (1,
                  'Severity: minor, Description: Broken, Cause: powerproblem, Code: F0883, '
                  'Affected DN: rack-unit-1/psu-4'),
                 (1,
                  'Severity: warning, Description: Broken, Cause: powerproblem, Code: F0883, '
                  'Affected DN: rack-unit-1/psu-4'),
                 (1,
                  'Severity: major, Description: Broken, Cause: powerproblem, Code: F0883, '
                  'Affected DN: rack-unit-1/psu-4'),
                 (2,
                  'Severity: critical, Description: Broken, Cause: powerproblem, Code: F0883, '
                  'Affected DN: rack-unit-1/psu-4'),
                 (3,
                  'Severity: unknown, Description: Broken, Cause: powerproblem, Code: F0883, '
                  'Affected DN: rack-unit-1/psu-4'),
                 ])
               ]}
