#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'openbsd_sensors'

info = [
    [u'temp0', u'0', u'30.00', u'degC', u'0'],
    [u'sd0', u'13', u'online', u'', u'1'],
    [u'CPU1 Temp', u'0', u'35.00', u'degC', u'1'],
    [u'CPU2 Temp', u'0', u'36.00', u'degC', u'1'],
    [u'PCH Temp', u'0', u'36.00', u'degC', u'1'],
    [u'System Temp', u'0', u'23.00', u'degC', u'1'],
    [u'Peripheral Temp', u'0', u'34.00', u'degC', u'1'],
    [u'Vcpu1VRM Temp', u'0', u'30.00', u'degC', u'1'],
    [u'Vcpu2VRM Temp', u'0', u'34.00', u'degC', u'1'],
    [u'VmemABVRM Temp', u'0', u'26.00', u'degC', u'1'],
    [u'VmemCDVRM Temp', u'0', u'34.00', u'degC', u'1'],
    [u'VmemEFVRM Temp', u'0', u'29.00', u'degC', u'1'],
    [u'VmemGHVRM Temp', u'0', u'28.00', u'degC', u'1'],
    [u'P1-DIMMA1 Temp', u'0', u'25.00', u'degC', u'1'],
    [u'P1-DIMMB1 Temp', u'0', u'25.00', u'degC', u'1'],
    [u'P1-DIMMC1 Temp', u'0', u'26.00', u'degC', u'1'],
    [u'P1-DIMMD1 Temp', u'0', u'24.00', u'degC', u'1'],
    [u'P2-DIMME1 Temp', u'0', u'28.00', u'degC', u'1'],
    [u'P2-DIMMF1 Temp', u'0', u'26.00', u'degC', u'1'],
    [u'P2-DIMMG1 Temp', u'0', u'27.00', u'degC', u'1'],
    [u'P2-DIMMH1 Temp', u'0', u'28.00', u'degC', u'1'],
    [u'MB/AOM_SAS Temp', u'0', u'46.00', u'degC', u'1'],
    [u'FAN1', u'1', u'3100', u'RPM', u'1'],
    [u'FAN3', u'1', u'3100', u'RPM', u'1'],
    [u'FANA', u'1', u'2600', u'RPM', u'1'],
    [u'12V', u'2', u'12.06', u'V DC', u'1'],
    [u'5VCC', u'2', u'5.08', u'V DC', u'1'],
    [u'3.3VCC', u'2', u'3.38', u'V DC', u'1'],
    [u'VBAT', u'2', u'2.98', u'V DC', u'1'],
    [u'Vcpu1', u'2', u'1.84', u'V DC', u'1'],
    [u'Vcpu2', u'2', u'1.84', u'V DC', u'1'],
    [u'VDIMMAB', u'2', u'1.21', u'V DC', u'1'],
    [u'VDIMMCD', u'2', u'1.21', u'V DC', u'1'],
    [u'VDIMMEF', u'2', u'1.21', u'V DC', u'1'],
    [u'VDIMMGH', u'2', u'1.21', u'V DC', u'1'],
    [u'5VSB', u'2', u'4.97', u'V DC', u'1'],
    [u'3.3VSB', u'2', u'3.30', u'V DC', u'1'],
    [u'1.5V PCH', u'2', u'1.52', u'V DC', u'1'],
    [u'1.2V BMC', u'2', u'1.22', u'V DC', u'1'],
    [u'1.05V PCH', u'2', u'1.06', u'V DC', u'1'],
    [u'Chassis Intru', u'9', u'off', u'', u'1'],
    [u'PS1 Status', u'21', u'present', u'', u'1'],
    [u'PS2 Status', u'21', u'present', u'', u'1']
]

discovery = {
    '': [
        (u'CPU1 Temp', {}), (u'CPU2 Temp', {}), (u'MB/AOM_SAS Temp', {}),
        (u'P1-DIMMA1 Temp', {}), (u'P1-DIMMB1 Temp', {}),
        (u'P1-DIMMC1 Temp', {}), (u'P1-DIMMD1 Temp', {}),
        (u'P2-DIMME1 Temp', {}), (u'P2-DIMMF1 Temp', {}),
        (u'P2-DIMMG1 Temp', {}), (u'P2-DIMMH1 Temp', {}), (u'PCH Temp', {}),
        (u'Peripheral Temp', {}), (u'System Temp', {}), (u'Vcpu1VRM Temp', {}),
        (u'Vcpu2VRM Temp', {}), (u'VmemABVRM Temp', {}),
        (u'VmemCDVRM Temp', {}), (u'VmemEFVRM Temp', {}),
        (u'VmemGHVRM Temp', {}), (u'temp0', {})
    ],
    'indicator': [(u'Chassis Intru', {})],
    'drive': [(u'sd0', {})],
    'powersupply': [(u'PS1 Status', {}), (u'PS2 Status', {})],
    'fan': [(u'FAN1', {}), (u'FAN3', {}), (u'FANA', {})],
    'voltage': [
        (u'1.05V PCH', {}), (u'1.2V BMC', {}), (u'1.5V PCH', {}), (u'12V', {}),
        (u'3.3VCC', {}), (u'3.3VSB', {}), (u'5VCC', {}), (u'5VSB', {}),
        (u'VBAT', {}), (u'VDIMMAB', {}), (u'VDIMMCD', {}), (u'VDIMMEF', {}),
        (u'VDIMMGH', {}), (u'Vcpu1', {}), (u'Vcpu2', {})
    ]
}

checks = {
    '': [
        (
            u'CPU1 Temp', {}, [
                (0, u'35.0 \xb0C', [('temp', 35.0, None, None, None, None)])
            ]
        ),
        (
            u'CPU2 Temp', {}, [
                (0, u'36.0 \xb0C', [('temp', 36.0, None, None, None, None)])
            ]
        ),
        (
            u'MB/AOM_SAS Temp', {}, [
                (0, u'46.0 \xb0C', [('temp', 46.0, None, None, None, None)])
            ]
        ),
        (
            u'P1-DIMMA1 Temp', {}, [
                (0, u'25.0 \xb0C', [('temp', 25.0, None, None, None, None)])
            ]
        ),
        (
            u'P1-DIMMB1 Temp', {}, [
                (0, u'25.0 \xb0C', [('temp', 25.0, None, None, None, None)])
            ]
        ),
        (
            u'P1-DIMMC1 Temp', {}, [
                (0, u'26.0 \xb0C', [('temp', 26.0, None, None, None, None)])
            ]
        ),
        (
            u'P1-DIMMD1 Temp', {}, [
                (0, u'24.0 \xb0C', [('temp', 24.0, None, None, None, None)])
            ]
        ),
        (
            u'P2-DIMME1 Temp', {}, [
                (0, u'28.0 \xb0C', [('temp', 28.0, None, None, None, None)])
            ]
        ),
        (
            u'P2-DIMMF1 Temp', {}, [
                (0, u'26.0 \xb0C', [('temp', 26.0, None, None, None, None)])
            ]
        ),
        (
            u'P2-DIMMG1 Temp', {}, [
                (0, u'27.0 \xb0C', [('temp', 27.0, None, None, None, None)])
            ]
        ),
        (
            u'P2-DIMMH1 Temp', {}, [
                (0, u'28.0 \xb0C', [('temp', 28.0, None, None, None, None)])
            ]
        ),
        (
            u'PCH Temp', {}, [
                (0, u'36.0 \xb0C', [('temp', 36.0, None, None, None, None)])
            ]
        ),
        (
            u'Peripheral Temp', {}, [
                (0, u'34.0 \xb0C', [('temp', 34.0, None, None, None, None)])
            ]
        ),
        (
            u'System Temp', {}, [
                (0, u'23.0 \xb0C', [('temp', 23.0, None, None, None, None)])
            ]
        ),
        (
            u'Vcpu1VRM Temp', {}, [
                (0, u'30.0 \xb0C', [('temp', 30.0, None, None, None, None)])
            ]
        ),
        (
            u'Vcpu2VRM Temp', {}, [
                (0, u'34.0 \xb0C', [('temp', 34.0, None, None, None, None)])
            ]
        ),
        (
            u'VmemABVRM Temp', {}, [
                (0, u'26.0 \xb0C', [('temp', 26.0, None, None, None, None)])
            ]
        ),
        (
            u'VmemCDVRM Temp', {}, [
                (0, u'34.0 \xb0C', [('temp', 34.0, None, None, None, None)])
            ]
        ),
        (
            u'VmemEFVRM Temp', {}, [
                (0, u'29.0 \xb0C', [('temp', 29.0, None, None, None, None)])
            ]
        ),
        (
            u'VmemGHVRM Temp', {}, [
                (0, u'28.0 \xb0C', [('temp', 28.0, None, None, None, None)])
            ]
        ),
        (
            u'temp0', {}, [
                (0, u'30.0 \xb0C', [('temp', 30.0, None, None, None, None)])
            ]
        )
    ],
    'indicator': [(u'Chassis Intru', {}, [(0, u'Status: off', [])])],
    'drive': [(u'sd0', {}, [(0, u'Status: online', [])])],
    'powersupply': [
        (u'PS1 Status', {}, [(0, u'Status: present', [])]),
        (u'PS2 Status', {}, [(0, u'Status: present', [])])
    ],
    'fan': [
        (
            u'FAN1', {
                'upper': (8000, 8400),
                'lower': (500, 300)
            }, [(0, 'Speed: 3100 RPM', [])]
        ),
        (
            u'FAN3', {
                'upper': (8000, 8400),
                'lower': (500, 300)
            }, [(0, 'Speed: 3100 RPM', [])]
        ),
        (
            u'FANA', {
                'upper': (8000, 8400),
                'lower': (500, 300)
            }, [(0, 'Speed: 2600 RPM', [])]
        )
    ],
    'voltage': [
        (
            u'1.05V PCH', {}, [
                (
                    0, 'Voltage: 1.1 V', [
                        ('voltage', 1.06, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'1.2V BMC', {}, [
                (
                    0, 'Voltage: 1.2 V', [
                        ('voltage', 1.22, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'1.5V PCH', {}, [
                (
                    0, 'Voltage: 1.5 V', [
                        ('voltage', 1.52, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'12V', {}, [
                (
                    0, 'Voltage: 12.1 V', [
                        ('voltage', 12.06, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'3.3VCC', {}, [
                (
                    0, 'Voltage: 3.4 V', [
                        ('voltage', 3.38, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'3.3VSB', {}, [
                (
                    0, 'Voltage: 3.3 V', [
                        ('voltage', 3.3, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'5VCC', {}, [
                (
                    0, 'Voltage: 5.1 V', [
                        ('voltage', 5.08, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'5VSB', {}, [
                (
                    0, 'Voltage: 5.0 V', [
                        ('voltage', 4.97, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'VBAT', {}, [
                (
                    0, 'Voltage: 3.0 V', [
                        ('voltage', 2.98, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'VDIMMAB', {}, [
                (
                    0, 'Voltage: 1.2 V', [
                        ('voltage', 1.21, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'VDIMMCD', {}, [
                (
                    0, 'Voltage: 1.2 V', [
                        ('voltage', 1.21, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'VDIMMEF', {}, [
                (
                    0, 'Voltage: 1.2 V', [
                        ('voltage', 1.21, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'VDIMMGH', {}, [
                (
                    0, 'Voltage: 1.2 V', [
                        ('voltage', 1.21, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'Vcpu1', {}, [
                (
                    0, 'Voltage: 1.8 V', [
                        ('voltage', 1.84, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'Vcpu2', {}, [
                (
                    0, 'Voltage: 1.8 V', [
                        ('voltage', 1.84, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
