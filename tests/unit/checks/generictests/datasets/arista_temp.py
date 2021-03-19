#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'arista_temp'

info = [
    ['48x 1000BASE-T + 4 SFP+ 1RU', '', ''], ['Scd Chip 2', '', ''],
    ['Cpu temp sensor', '1', '375'], ['Front internal sensor', '1', '200'],
    ['Front external sensor', '1',
     '163'], ['Rear internal sensor', '1', '280'],
    ['Rear external sensor', '1', '228'], ['Switch ASIC Center', '1', '379'],
    ['Switch ASIC Lower Left Corner', '1', '390'],
    ['Switch ASIC Upper Right Edge', '1', '379'], ['Ethernet1', '', ''],
    ['Xcvr Slot 35', '', ''], ['Xcvr for Ethernet35', '', ''],
    ['DOM Temperature Sensor for Ethernet49', '1', '252'],
    ['DOM Voltage Sensor for Ethernet49', '2', '335'],
    ['Lane 0 for Xcvr for Ethernet49', '', ''],
    ['DOM TX Bias Sensor for Ethernet49', '2', '847'],
    ['DOM TX Power Sensor for Ethernet49', '4', '6582'],
    ['DOM RX Power Sensor for Ethernet49', '4', '5412'],
    ['Xcvr Slot 50', '', ''], ['Xcvr for Ethernet50', '', ''],
    ['DOM Temperature Sensor for Ethernet50', '1', '260'],
    ['DOM Voltage Sensor for Ethernet50', '2', '341'],
    ['Lane 0 for Xcvr for Ethernet50', '', ''],
    ['DOM TX Bias Sensor for Ethernet50', '2', '848'],
    ['DOM TX Power Sensor for Ethernet50', '4', '6108'],
    ['DOM RX Power Sensor for Ethernet50', '4', '5677'],
    ['Xcvr Slot 51', '', ''], ['Xcvr for Ethernet51', '', ''],
    ['Xcvr Slot 52', '', ''], ['Xcvr for Ethernet52', '', ''],
    ['Fan Tray Slot 1', '', ''], ['Fan Tray 1', '', ''],
    ['Fan Tray 1 Fan 1', '', ''], ['Fan Tray 1 Fan 1 Sensor 1', '0', '5000'],
    ['Fan Tray Slot 2', '', ''], ['Fan Tray 2', '', ''],
    ['Fan Tray 2 Fan 1', '', ''], ['Fan Tray 2 Fan 1 Sensor 1', '0', '5000'],
    ['power Supply Slot 1', '', ''], ['PowerSupply1', '', ''],
    ['power Supply Slot 2', '', ''], ['PowerSupply2', '', ''],
    ['Chip Container', '', ''], ['Sensor Container', '', ''],
    ['Port Container', '', ''], ['Xcvr Slot Container', '', ''],
    ['Fan Tray Slot Container', '', ''],
    ['Power Supply Slot Container', '', ''],
    ['Power Supply Sensor Container', '', ''],
    ['Power Supply Fan Container', '', ''],
    ['Power Supply Sensor Container', '', ''],
    ['Power Supply Fan Container', '', '']
]

discovery = {
    '': [
        ('Cpu temp sensor', {}), ('DOM Temperature Sensor for Ethernet49', {}),
        ('DOM Temperature Sensor for Ethernet50', {})
    ]
}

checks = {
    '': [
        (
            'Cpu temp sensor', {}, [
                (0, '37.5 °C', [('temp', 37.5, None, None, None, None)])
            ]
        ),
        (
            'DOM Temperature Sensor for Ethernet49', {}, [
                (
                    0, '25.2 °C', [
                        ('temp', 25.200000000000003, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'DOM Temperature Sensor for Ethernet50', {}, [
                (0, '26.0 °C', [('temp', 26.0, None, None, None, None)])
            ]
        )
    ]
}
