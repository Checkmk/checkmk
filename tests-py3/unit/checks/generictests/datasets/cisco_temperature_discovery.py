#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'cisco_temperature'


info = [[[u'300000013', u'Ethernet1/1 Lane 1 Transceiver Receive Power Sensor'],
         [u'300000014', u'Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor'],
         [u'300003533', u'Ethernet1/3 Lane 1 Transceiver Receive Power Sensor'],
         [u'300003534', u'Ethernet1/3 Lane 1 Transceiver Transmit Power Sensor'],
         [u'300005293', u'Ethernet1/4 Lane 1 Transceiver Receive Power Sensor'],
         [u'300005294', u'Ethernet1/4 Lane 1 Transceiver Transmit Power Sensor']],
        [[u'300000013', u'14', u'8', u'0', u'-3271', u'1'],
         [u'300000014', u'14', u'8', u'0', u'1000', u'1'],
         [u'300003533', u'14', u'8', u'0', u'-2823', u'1'],
         [u'300003534', u'14', u'8', u'0', u'-1000', u'1'],
         [u'300005293', u'14', u'8', u'0', u'-40000', u'1'],
         [u'300005294', u'14', u'8', u'0', u'0', u'1']],
        [[u'300000013.1', u'2000'],
         [u'300000013.2', u'-1000'],
         [u'300000013.3', u'-13904'],
         [u'300000013.4', u'-9901'],
         [u'300000014.1', u'1699'],
         [u'300000014.2', u'-1300'],
         [u'300000014.3', u'-11301'],
         [u'300000014.4', u'-7300'],
         [u'300003533.1', u'2000'],
         [u'300003533.2', u'-1000'],
         [u'300003533.3', u'-13904'],
         [u'300003533.4', u'-9901'],
         [u'300003534.1', u'1699'],
         [u'300003534.2', u'-1300'],
         [u'300003534.3', u'-11301'],
         [u'300003534.4', u'-7300'],
         [u'300005293.1', u'2000'],
         [u'300005293.2', u'-1000'],
         [u'300005293.3', u'-13904'],
         [u'300005293.4', u'-9901'],
         [u'300005294.1', u'1699'],
         [u'300005294.2', u'-1300'],
         [u'300005294.3', u'-11301'],
         [u'300005294.4', u'-7300']],
        [],
        [[u'Ethernet1/1 Lane 1 Transceiver Receive Power Sensor', u'1'],
         [u'Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor', u'1'],
         [u'Ethernet1/3 Lane 1 Transceiver Receive Power Sensor', u'2'],
         [u'Ethernet1/3 Lane 1 Transceiver Transmit Power Sensor', u'2'],
         [u'Ethernet1/4 Lane 1 Transceiver Receive Power Sensor', u'3'],
         [u'Ethernet1/4 Lane 1 Transceiver Transmit Power Sensor', u'3']],
        []]


discovery = {'': [],
             'dom': [(u'Ethernet1/1 Lane 1 Transceiver Receive Power Sensor', {}),
                     (u'Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor', {}),
                     (u'Ethernet1/4 Lane 1 Transceiver Receive Power Sensor', {}),
                     (u'Ethernet1/4 Lane 1 Transceiver Transmit Power Sensor', {})]}


checks = {'dom': [(u'Ethernet1/1 Lane 1 Transceiver Receive Power Sensor',
                   {},
                   [(0, 'Status: OK', []),
                    (0,
                     'Signal power: -3.27 dBm',
                     [('input_signal_power_dbm', -3.271, -1.0, 2.0, None, None)])]),
                  (u'Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor',
                   {},
                   [(0, 'Status: OK', []),
                    (1,
                     'Signal power: 1.00 dBm (warn/crit at -1.30 dBm/1.70 dBm)',
                     [('output_signal_power_dbm', 1.0, -1.3, 1.699, None, None)])]),
                  (u'Ethernet1/4 Lane 1 Transceiver Receive Power Sensor',
                   {},
                   [(0, 'Status: OK', []),
                    (2,
                     'Signal power: -40.00 dBm (warn/crit below -9.90 dBm/-13.90 dBm)',
                     [('input_signal_power_dbm', -40.0, -1.0, 2.0, None, None)])]),
                  (u'Ethernet1/4 Lane 1 Transceiver Transmit Power Sensor',
                   {},
                   [(0, 'Status: OK', []),
                    (1,
                     'Signal power: 0.00 dBm (warn/crit at -1.30 dBm/1.70 dBm)',
                     [('output_signal_power_dbm', 0.0, -1.3, 1.699, None, None)])])]}


mock_host_conf_merged = {'dom': {'admin_states': ['1', '3']}}
