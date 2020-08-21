#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

# Notes:
# docker0 has ifInOctets == 0.
# - If docker0 is not updated with ip address statistics we get:
#   'ifInOctects == 0' => 'ifOperState == 4'
#   => The interface is not discovered
# - ip address statistics contain <UP>; we get 'ifOperState == 1'
#   and the docker0 interface will be discovered.

from cmk.base.plugins.agent_based.lnx_if import parse_lnx_if

checkname = 'lnx_if'

parsed = parse_lnx_if([
    [u'[start_iplink]'],
    [u'1:',
     u'lo:',
     u'<LOOPBACK,UP,LOWER_UP>',
     u'mtu',
     u'65536',
     u'qdisc',
     u'noqueue',
     u'state',
     u'UNKNOWN',
     u'mode',
     u'DEFAULT',
     u'group',
     u'default',
     u'qlen',
     u'1000'],
    [u'link/loopback', u'00:00:00:00:00:00', u'brd', u'00:00:00:00:00:00'],
    [u'2:',
     u'wlp3s0:',
     u'<BROADCAST,MULTICAST,UP,LOWER_UP>',
     u'mtu',
     u'1500',
     u'qdisc',
     u'fq_codel',
     u'state',
     u'UP',
     u'mode',
     u'DORMANT',
     u'group',
     u'default',
     u'qlen',
     u'1000'],
    [u'link/ether', u'AA:AA:AA:AA:AA:BB', u'brd', u'BB:BB:BB:BB:BB:BB'],
    [u'3:',
     u'docker0:',
     u'<BROADCAST,MULTICAST,UP,LOWER_UP>',
     u'mtu',
     u'1500',
     u'qdisc',
     u'noqueue',
     u'state',
     u'UP',
     u'mode',
     u'DEFAULT',
     u'group',
     u'default'],
    [u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB'],
    [u'5:',
     u'veth6a06585@if4:',
     u'<BROADCAST,MULTICAST,UP,LOWER_UP>',
     u'mtu',
     u'1500',
     u'qdisc',
     u'noqueue',
     u'master',
     u'docker0',
     u'state',
     u'UP',
     u'mode',
     u'DEFAULT',
     u'group',
     u'default'],
    [u'link/ether',
     u'AA:AA:AA:AA:AA:AA',
     u'brd',
     u'BB:BB:BB:BB:BB:BB',
     u'link-netnsid',
     u'0'],
    [u'[end_iplink]'],
    [u'lo',
     u' 164379850  259656    0    0    0     0          0         0 164379850  259656    0    0    0     0       0          0'],
    [u'wlp3s0',
     u' 130923553  201184    0    0    0     0          0     16078 23586281  142684    0    0    0     0       0          0'],
    [u'docker0',
     u'       0       0    0    0    0     0          0         0    16250     184    0    0    0     0       0          0'],
    [u'veth6a06585',
     u'       0       0    0    0    0     0          0         0    25963     287    0    0    0     0       0          0'],
])

discovery = {'': [('1', "{'state': ['1'], 'speed': 0}"),
                  ('4', "{'state': ['1'], 'speed': 0}")]}

checks = {'': [('1',
                {'errors': (0.01, 0.1), 'speed': 0, 'state': ['1']},
                [(0, '[docker0] (up) MAC: AA:AA:AA:AA:AA:AA, speed unknown', [])]),
               ('4',
                {'errors': (0.01, 0.1), 'speed': 0, 'state': ['1']},
                [(0, '[wlp3s0] (up) MAC: AA:AA:AA:AA:AA:BB, speed unknown', [])])]}
