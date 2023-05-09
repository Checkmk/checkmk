#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'ewon'

info = [
    [u'1', u'0', u'System'], [u'2', u'0', u'System'], [u'3', u'0', u'System'],
    [u'4', u'8192', u'System'], [u'5', u'1', u'N2-Versorgung'],
    [u'6', u'0', u'Betriebsraum'], [u'7', u'0', u'Betriebsraum'],
    [u'8', u'0', u'Flur_Nebenraum'], [u'9', u'0', u'Flur_Nebenraum'],
    [u'10', u'1527', u'Schutzbereich01'], [u'11', u'1550', u'Schutzbereich01'],
    [u'12', u'1550', u'Schutzbereich01'], [u'13', u'1520', u'Schutzbereich01'],
    [u'14', u'0', u'Schutzbereich01'], [u'15', u'1029', u'Schutzbereich01'],
    [u'16', u'512', u'Schutzbereich01'], [u'17', u'513', u'Schutzbereich01'],
    [u'18', u'1539', u'Schutzbereich02'], [u'19', u'1550', u'Schutzbereich02'],
    [u'20', u'1550', u'Schutzbereich02'], [u'21', u'1520', u'Schutzbereich02'],
    [u'22', u'0', u'Schutzbereich02'], [u'23', u'1029', u'Schutzbereich02'],
    [u'24', u'512', u'Schutzbereich02'], [u'25', u'513', u'Schutzbereich02'],
    [u'26', u'1533', u'Schutzbereich03'], [u'27', u'1550', u'Schutzbereich03'],
    [u'28', u'1550', u'Schutzbereich03'], [u'29', u'1520', u'Schutzbereich03'],
    [u'30', u'0', u'Schutzbereich03'], [u'31', u'1029', u'Schutzbereich03'],
    [u'32', u'512', u'Schutzbereich03'], [u'33', u'513', u'Schutzbereich03'],
    [u'34', u'0', u'Schutzbereich04'], [u'35', u'0', u'Schutzbereich04'],
    [u'36', u'0', u'Schutzbereich04'], [u'37', u'0', u'Schutzbereich04'],
    [u'38', u'0', u'Schutzbereich04'], [u'39', u'0', u'Schutzbereich04'],
    [u'40', u'0', u'Schutzbereich04'], [u'41', u'0', u'Schutzbereich04']
]


mock_host_conf = {'': ['oxyreduct']}


discovery = {
    '': [
        ('eWON Status', {'device': 'oxyreduct'}),
        (u'Betriebsraum', {'device': 'oxyreduct'}),
        (u'Flur_Nebenraum', {'device': 'oxyreduct'}),
        (u'N2-Versorgung', {'device': 'oxyreduct'}),
        (u'Schutzbereich01', {'device': 'oxyreduct'}),
        (u'Schutzbereich02', {'device': 'oxyreduct'}),
        (u'Schutzbereich03', {'device': 'oxyreduct'}),
        (u'System', {'device': 'oxyreduct'}),
    ]
}


checks = {
    '': [
        ('eWON Status', {'device': 'oxyreduct'}, [
            (0, 'Configured for oxyreduct', []),
        ]),
        (u'Betriebsraum', {'device': 'oxyreduct'}, [
            (0, 'O2 Sensor inactive', []),
        ]),
        (u'Flur_Nebenraum', {'device': 'oxyreduct'}, [
            (0, 'O2 Sensor inactive', []),
        ]),
        (u'N2-Versorgung', {'device': 'oxyreduct'}, [
            (0, 'N2 to safe area inactive', []),
            (0, 'N2 request from safe area inactive', []),
            (2, 'N2 via compressor inactive', []),
        ]),
        (u'Schutzbereich01', {'device': 'oxyreduct'}, [
            (0, 'O2 average: 15.27 %', [
                ('o2_percentage', 15.27, 16, 17, None, None),
            ]),
            (0, 'O2 target: 15.50 %', []),
            (0, 'O2 for N2-in: 15.50 %', []),
            (0, 'O2 for N2-out: 15.20 %', []),
            (0, 'CO2 maximum: 0.00 ppm', []),
            (0, 'air control closed', []),
            (0, 'valve closed', []),
            (0, 'valve active', []),
            (0, 'access open', []),
            (0, 'mode BK1', []),
        ]),
        (u'System', {'device': 'oxyreduct'}, [
            (0, 'alarms: 0.00', []),
            (0, 'incidents: 0.00', []),
            (0, 'shutdown messages: 0.00', []),
            (2, 'luminous field active', []),
        ]),
    ],
}
