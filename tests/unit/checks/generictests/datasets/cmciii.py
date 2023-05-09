#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'cmciii'

info = [
    [
        ['1', 'CMCIII-PU', 'CMC-PU', '2'],
        ['2', 'CMCIII-IO3', 'CMC-IOModul', '2'],
        ['3', 'CMCIII-HUM', 'CMC-Temperatur', '2'],
        ['4', 'CMCIII-SMK', 'CMC-Rauchmelder', '2']
    ],
    [
        ['1.1', 'Temperature.DescName', '1', '', '0', 'Temperature', '0'],
        [
            '1.2', 'Temperature.Value', '2', 'degree C', '-100',
            '30.50 degree C', '3050'
        ],
        [
            '1.3', 'Temperature.Offset', '18', 'degree C', '',
            '0.00 degree C', '0'
        ],
        [
            '1.4', 'Temperature.SetPtHighAlarm', '3', 'degree C', '-100',
            '45.00 degree C', '4500'
        ],
        [
            '1.5', 'Temperature.SetPtHighWarning', '4', 'degree C', '-100',
            '40.00 degree C', '4000'
        ],
        [
            '1.6', 'Temperature.SetPtLowWarning', '9', 'degree C', '-100',
            '10.00 degree C', '1000'
        ],
        [
            '1.7', 'Temperature.SetPtLowAlarm', '5', 'degree C', '-100',
            '5.00 degree C', '500'
        ],
        ['1.8', 'Temperature.Hysteresis', '6', '%', '-100', '5.00 %', '500'],
        ['1.9', 'Temperature.Status', '7', '', '0', 'OK', '4'],
        ['1.10', 'Temperature.Category', '14', '', '0', '16', '16'],
        ['1.11', 'Access.DescName', '1', '', '0', 'Door', '0'],
        ['1.12', 'Access.Value', '2', '', '1', '0', '0'],
        ['1.13', 'Access.Sensitivity', '30', '', '1', '0', '0'],
        ['1.14', 'Access.Delay', '21', 's', '1', '10 s', '10'],
        ['1.15', 'Access.Status', '7', '', '0', 'Inactive', '27'],
        ['1.16', 'Access.Category', '14', '', '0', '192', '192'],
        ['1.17', 'Input 1.DescName', '1', '', '0', 'Input_1', '0'],
        ['1.18', 'Input 1.Value', '2', '', '1', '0', '0'],
        ['1.19', 'Input 1.Logic', '15', '', '0', '0:Off / 1:On', '0'],
        ['1.20', 'Input 1.Delay', '21', 's', '-10', '0.5 s', '5'],
        ['1.21', 'Input 1.Status', '7', '', '0', 'Off', '10'],
        ['1.22', 'Input 1.Category', '14', '', '0', '16', '16'],
        ['1.23', 'Input 2.DescName', '1', '', '0', 'Input_2', '0'],
        ['1.24', 'Input 2.Value', '2', '', '1', '0', '0'],
        ['1.25', 'Input 2.Logic', '15', '', '0', '0:Off / 1:On', '0'],
        ['1.26', 'Input 2.Delay', '21', 's', '-10', '0.5 s', '5'],
        ['1.27', 'Input 2.Status', '7', '', '0', 'Off', '10'],
        ['1.28', 'Input 2.Category', '14', '', '0', '16', '16'],
        ['1.29', 'Output.DescName', '1', '', '0', 'Alarm Relay', '0'],
        ['1.30', 'Output.Relay', '20', '', '0', 'Off', '0'],
        ['1.31', 'Output.Logic', '15', '', '0', '0:Off / 1:On', '0'],
        ['1.32', 'Output.Status', '7', '', '0', 'Off', '10'],
        ['1.33', 'Output.Category', '14', '', '0', '16', '16'],
        ['1.34', 'System.V24 Port.DescName', '1', '', '0', 'V24 Unit', '0'],
        [
            '1.35', 'System.V24 Port.Message', '95', '', '0',
            'no SMS unit found', '0'
        ], ['1.36', 'System.V24 Port.Signal', '2', '%', '1', '0 %', '0'],
        ['1.37', 'System.V24 Port.Status', '7', '', '0', 'n.a.', '1'],
        ['1.38', 'System.V24 Port.Category', '14', '', '0', '16', '16'],
        [
            '1.39', 'System.CAN1 Current.DescName', '1', '', '0',
            'CAN1 Current', '0'
        ], ['1.40', 'System.CAN1 Current.Value', '2', 'mA', '1', '0 mA', '0'],
        [
            '1.41', 'System.CAN1 Current.SetPtHighAlarm', '3', 'mA', '1',
            '900 mA', '900'
        ],
        [
            '1.42', 'System.CAN1 Current.SetPtHighWarning', '4', 'mA', '1',
            '700 mA', '700'
        ],
        [
            '1.43', 'System.CAN1 Current.Hysteresis', '6', '%', '-100',
            '5.00 %', '500'
        ], ['1.44', 'System.CAN1 Current.Status', '7', '', '0', 'OK', '4'],
        ['1.45', 'System.CAN1 Current.Category', '14', '', '0', '16', '16'],
        [
            '1.46', 'System.CAN2 Current.DescName', '1', '', '0',
            'CAN2 Current', '0'
        ], ['1.47', 'System.CAN2 Current.Value', '2', 'mA', '1', '0 mA', '0'],
        [
            '1.48', 'System.CAN2 Current.SetPtHighAlarm', '3', 'mA', '1',
            '900 mA', '900'
        ],
        [
            '1.49', 'System.CAN2 Current.SetPtHighWarning', '4', 'mA', '1',
            '700 mA', '700'
        ],
        [
            '1.50', 'System.CAN2 Current.Hysteresis', '6', '%', '-100',
            '5.00 %', '500'
        ], ['1.51', 'System.CAN2 Current.Status', '7', '', '0', 'OK', '4'],
        ['1.52', 'System.CAN2 Current.Category', '14', '', '0', '16', '16'],
        ['1.53', 'System.Temperature.DescName', '1', '', '0', 'Sys Temp', '0'],
        [
            '1.54', 'System.Temperature.Value', '2', 'degree C', '-100',
            '32.30 degree C', '3230'
        ],
        [
            '1.55', 'System.Temperature.Offset', '18', 'degree C', '-100',
            '0.00 degree C', '0'
        ],
        [
            '1.56', 'System.Temperature.SetPtHighAlarm', '3', 'degree C',
            '-100', '80.00 degree C', '8000'
        ],
        [
            '1.57', 'System.Temperature.SetPtHighWarning', '4', 'degree C',
            '-100', '70.00 degree C', '7000'
        ],
        [
            '1.58', 'System.Temperature.SetPtLowWarning', '9', 'degree C',
            '-100', '-25.00 degree C', '-2500'
        ],
        [
            '1.59', 'System.Temperature.SetPtLowAlarm', '5', 'degree C',
            '-100', '-30.00 degree C', '-3000'
        ],
        [
            '1.60', 'System.Temperature.Hysteresis', '6', '%', '-100',
            '10.00 %', '1000'
        ], ['1.61', 'System.Temperature.Status', '7', '', '0', 'OK', '4'],
        ['1.62', 'System.Temperature.Category', '14', '', '0', '16', '16'],
        [
            '1.63', 'System.Supply 24V.DescName', '1', '', '0', 'Supply 24V',
            '0'
        ],
        [
            '1.64', 'System.Supply 24V.Value', '2', 'V', '-1000', '23.510 V',
            '23510'
        ],
        [
            '1.65', 'System.Supply 24V.SetPtHighAlarm', '3', 'V', '-1000',
            '28.000 V', '28000'
        ],
        [
            '1.66', 'System.Supply 24V.SetPtHighWarning', '4', 'V', '-1000',
            '26.000 V', '26000'
        ],
        [
            '1.67', 'System.Supply 24V.SetPtLowWarning', '9', 'V', '-1000',
            '21.000 V', '21000'
        ],
        [
            '1.68', 'System.Supply 24V.SetPtLowAlarm', '5', 'V', '-1000',
            '19.000 V', '19000'
        ],
        [
            '1.69', 'System.Supply 24V.Hysteresis', '6', '%', '-100',
            '10.00 %', '1000'
        ], ['1.70', 'System.Supply 24V.Status', '7', '', '0', 'OK', '4'],
        ['1.71', 'System.Supply 24V.Category', '14', '', '0', '16', '16'],
        [
            '1.72', 'System.Supply 5V0.DescName', '1', '', '0', 'Supply 5V0',
            '0'
        ],
        [
            '1.73', 'System.Supply 5V0.Value', '2', 'V', '-1000', '5.000 V',
            '5000'
        ],
        [
            '1.74', 'System.Supply 5V0.SetPtHighAlarm', '3', 'V', '-1000',
            '5.500 V', '5500'
        ],
        [
            '1.75', 'System.Supply 5V0.SetPtHighWarning', '4', 'V', '-1000',
            '5.400 V', '5400'
        ],
        [
            '1.76', 'System.Supply 5V0.SetPtLowWarning', '9', 'V', '-1000',
            '4.600 V', '4600'
        ],
        [
            '1.77', 'System.Supply 5V0.SetPtLowAlarm', '5', 'V', '-1000',
            '4.500 V', '4500'
        ],
        [
            '1.78', 'System.Supply 5V0.Hysteresis', '6', '%', '-100', '2.00 %',
            '200'
        ], ['1.79', 'System.Supply 5V0.Status', '7', '', '0', 'OK', '4'],
        ['1.80', 'System.Supply 5V0.Category', '14', '', '0', '16', '16'],
        [
            '1.81', 'System.Supply 3V3.DescName', '1', '', '0', 'Supply 3V3',
            '0'
        ],
        [
            '1.82', 'System.Supply 3V3.Value', '2', 'V', '-1000', '3.290 V',
            '3290'
        ],
        [
            '1.83', 'System.Supply 3V3.SetPtHighAlarm', '3', 'V', '-1000',
            '3.630 V', '3630'
        ],
        [
            '1.84', 'System.Supply 3V3.SetPtHighWarning', '4', 'V', '-1000',
            '3.560 V', '3560'
        ],
        [
            '1.85', 'System.Supply 3V3.SetPtLowWarning', '9', 'V', '-1000',
            '3.040 V', '3040'
        ],
        [
            '1.86', 'System.Supply 3V3.SetPtLowAlarm', '5', 'V', '-1000',
            '2.970 V', '2970'
        ],
        [
            '1.87', 'System.Supply 3V3.Hysteresis', '6', '%', '-100', '2.00 %',
            '200'
        ], ['1.88', 'System.Supply 3V3.Status', '7', '', '0', 'OK', '4'],
        ['1.89', 'System.Supply 3V3.Category', '14', '', '0', '16', '16'],
        ['1.90', 'Memory.USB-Stick.DescName', '1', '', '0', 'USB-Stick', '0'],
        ['1.91', 'Memory.USB-Stick.Size', '2', 'GB', '-10', '0.0 GB', '0'],
        ['1.92', 'Memory.USB-Stick.Usage', '2', '%', '1', '0 %', '0'],
        ['1.93', 'Memory.USB-Stick.Command', '81', '', '0', '--', '4'],
        ['1.94', 'Memory.USB-Stick.Status', '7', '', '0', 'n.a.', '1'],
        ['1.95', 'Memory.USB-Stick.Category', '14', '', '0', '16', '16'],
        ['1.96', 'Memory.SD-Card.DescName', '1', '', '0', 'SD-Card', '0'],
        ['1.97', 'Memory.SD-Card.Size', '2', 'GB', '-10', '0.0 GB', '0'],
        ['1.98', 'Memory.SD-Card.Usage', '2', '%', '1', '0 %', '0'],
        ['1.99', 'Memory.SD-Card.Command', '81', '', '0', '--', '4'],
        ['1.100', 'Memory.SD-Card.Status', '7', '', '0', 'n.a.', '1'],
        ['1.101', 'Memory.SD-Card.Category', '14', '', '0', '16', '16'],
        ['1.102', 'Webcam.DescName', '1', '', '0', 'Webcam', '0'],
        ['1.103', 'Webcam.Command', '81', '', '0', '--', '4'],
        ['1.104', 'Webcam.Status', '7', '', '0', 'n.a.', '1'],
        ['1.105', 'Webcam.Category', '14', '', '0', '16', '16'],
        ['2.1', 'Input 1.DescName', '1', '', '0', 'Super Input', '0'],
        ['2.2', 'Input 1.Value', '2', '', '1', '0', '0'],
        ['2.3', 'Input 1.Logic', '15', '', '0', '0:OK / 1:Alarm', '2'],
        ['2.4', 'Input 1.Delay', '21', 's', '-10', '5.0 s', '50'],
        ['2.5', 'Input 1.Status', '7', '', '0', 'OK', '4'],
        ['2.6', 'Input 1.Category', '14', '', '0', '0', '0'],
        ['2.7', 'Input 2.DescName', '1', '', '0', 'Duper Input', '0'],
        ['2.8', 'Input 2.Value', '2', '', '1', '0', '0'],
        ['2.9', 'Input 2.Logic', '15', '', '0', '0:OK / 1:Alarm', '2'],
        ['2.10', 'Input 2.Delay', '21', 's', '-10', '5.0 s', '50'],
        ['2.11', 'Input 2.Status', '7', '', '0', 'OK', '4'],
        ['2.12', 'Input 2.Category', '14', '', '0', '0', '0'],
        [
            '2.13', 'Input 3.DescName', '1', '', '0', 'Blitzschutz',
            '0'
        ], ['2.14', 'Input 3.Value', '2', '', '1', '1', '1'],
        ['2.15', 'Input 3.Logic', '15', '', '0', '0:On / 1:Off', '1'],
        ['2.16', 'Input 3.Delay', '21', 's', '-10', '5.0 s', '50'],
        ['2.17', 'Input 3.Status', '7', '', '0', 'Off', '10'],
        ['2.18', 'Input 3.Category', '14', '', '0', '0', '0'],
        ['2.19', 'Input 4.DescName', '1', '', '0', 'Rote Tuer', '0'],
        ['2.20', 'Input 4.Value', '2', '', '1', '1', '1'],
        ['2.21', 'Input 4.Logic', '15', '', '0', '0:Alarm / 1:OK', '3'],
        ['2.22', 'Input 4.Delay', '21', 's', '-10', '0.5 s', '5'],
        ['2.23', 'Input 4.Status', '7', '', '0', 'OK', '4'],
        ['2.24', 'Input 4.Category', '14', '', '0', '0', '0'],
        ['2.25', 'Input 5.DescName', '1', '', '0', 'Gelbe Tuer', '0'],
        ['2.26', 'Input 5.Value', '2', '', '1', '1', '1'],
        ['2.27', 'Input 5.Logic', '15', '', '0', '0:Alarm / 1:OK', '3'],
        ['2.28', 'Input 5.Delay', '21', 's', '-10', '0.5 s', '5'],
        ['2.29', 'Input 5.Status', '7', '', '0', 'OK', '4'],
        ['2.30', 'Input 5.Category', '14', '', '0', '0', '0'],
        ['2.31', 'Input 6.DescName', '1', '', '0', 'Gruene Tuer', '0'],
        ['2.32', 'Input 6.Value', '2', '', '1', '1', '1'],
        ['2.33', 'Input 6.Logic', '15', '', '0', '0:Alarm / 1:OK', '3'],
        ['2.34', 'Input 6.Delay', '21', 's', '-10', '0.5 s', '5'],
        ['2.35', 'Input 6.Status', '7', '', '0', 'OK', '4'],
        ['2.36', 'Input 6.Category', '14', '', '0', '0', '0'],
        ['2.37', 'Input 7.DescName', '1', '', '0', 'Input_7', '0'],
        ['2.38', 'Input 7.Value', '2', '', '1', '0', '0'],
        ['2.39', 'Input 7.Logic', '15', '', '0', '0:Off / 1:On', '0'],
        ['2.40', 'Input 7.Delay', '21', 's', '-10', '0.5 s', '5'],
        ['2.41', 'Input 7.Status', '7', '', '0', 'Off', '10'],
        ['2.42', 'Input 7.Category', '14', '', '0', '0', '0'],
        ['2.43', 'Input 8.DescName', '1', '', '0', 'Input_8', '0'],
        ['2.44', 'Input 8.Value', '2', '', '1', '0', '0'],
        ['2.45', 'Input 8.Logic', '15', '', '0', '0:Off / 1:On', '0'],
        ['2.46', 'Input 8.Delay', '21', 's', '-10', '0.5 s', '5'],
        ['2.47', 'Input 8.Status', '7', '', '0', 'Off', '10'],
        ['2.48', 'Input 8.Category', '14', '', '0', '0', '0'],
        ['2.49', 'Output 1.DescName', '1', '', '0', 'Maxihub', '0'],
        ['2.50', 'Output 1.Relay', '20', '', '0', 'Off', '0'],
        ['2.51', 'Output 1.Grouping', '100', '', '0', '0', '0'],
        ['2.52', 'Output 1.Logic', '15', '', '0', '0:OK / 1:Alarm', '2'],
        ['2.53', 'Output 1.Status', '7', '', '0', 'OK', '4'],
        ['2.54', 'Output 1.Category', '14', '', '0', '0', '0'],
        ['2.55', 'Output 2.DescName', '1', '', '0', 'Output_2', '0'],
        ['2.56', 'Output 2.Relay', '20', '', '0', 'Off', '0'],
        ['2.57', 'Output 2.Grouping', '100', '', '0', '0', '0'],
        ['2.58', 'Output 2.Logic', '15', '', '0', '0:OK / 1:Alarm', '2'],
        ['2.59', 'Output 2.Status', '7', '', '0', 'OK', '4'],
        ['2.60', 'Output 2.Category', '14', '', '0', '0', '0'],
        ['2.61', 'Output 3.DescName', '1', '', '0', 'Output_3', '0'],
        ['2.62', 'Output 3.Relay', '20', '', '0', 'Off', '0'],
        ['2.63', 'Output 3.Grouping', '100', '', '0', '0', '0'],
        ['2.64', 'Output 3.Logic', '15', '', '0', '0:OK / 1:Alarm', '2'],
        ['2.65', 'Output 3.Status', '7', '', '0', 'OK', '4'],
        ['2.66', 'Output 3.Category', '14', '', '0', '0', '0'],
        ['2.67', 'Output 4.DescName', '1', '', '0', 'Output_4', '0'],
        ['2.68', 'Output 4.Relay', '20', '', '0', 'Off', '0'],
        ['2.69', 'Output 4.Grouping', '100', '', '0', '0', '0'],
        ['2.70', 'Output 4.Logic', '15', '', '0', '0:OK / 1:Alarm', '2'],
        ['2.71', 'Output 4.Status', '7', '', '0', 'OK', '4'],
        ['2.72', 'Output 4.Category', '14', '', '0', '0', '0'],
        ['3.1', 'Temperature.DescName', '1', '', '0', 'Temperature', '0'],
        [
            '3.2', 'Temperature.Value', '2', 'degree C', '-100',
            '27.00 degree C', '2700'
        ],
        [
            '3.3', 'Temperature.Offset', '18', 'degree C', '-100',
            '0.00 degree C', '0'
        ],
        [
            '3.4', 'Temperature.SetPtHighAlarm', '3', 'degree C', '-100',
            '40.00 degree C', '4000'
        ],
        [
            '3.5', 'Temperature.SetPtHighWarning', '4', 'degree C', '-100',
            '35.00 degree C', '3500'
        ],
        [
            '3.6', 'Temperature.SetPtLowWarning', '9', 'degree C', '-100',
            '10.00 degree C', '1000'
        ],
        [
            '3.7', 'Temperature.SetPtLowAlarm', '5', 'degree C', '-100',
            '5.00 degree C', '500'
        ], ['3.8', 'Temperature.Hysteresis', '6', '%', '-100', '0.00 %', '0'],
        ['3.9', 'Temperature.Status', '7', '', '0', 'OK', '4'],
        ['3.10', 'Temperature.Category', '14', '', '0', '80', '80'],
        ['3.11', 'Humidity.DescName', '1', '', '0', 'Humidity', '0'],
        ['3.12', 'Humidity.Value', '2', '%', '-100', '9.50 %', '950'],
        ['3.13', 'Humidity.Offset', '18', '%', '-100', '0.00 %', '0'],
        [
            '3.14', 'Humidity.SetPtHighAlarm', '3', '%', '-100', '80.00 %',
            '8000'
        ],
        [
            '3.15', 'Humidity.SetPtHighWarning', '4', '%', '-100', '75.00 %',
            '7500'
        ],
        [
            '3.16', 'Humidity.SetPtLowWarning', '9', '%', '-100', '10.00 %',
            '1000'
        ],
        ['3.17', 'Humidity.SetPtLowAlarm', '5', '%', '-100', '5.00 %', '500'],
        ['3.18', 'Humidity.Hysteresis', '6', '%', '-100', '0.00 %', '0'],
        ['3.19', 'Humidity.Status', '7', '', '0', 'Low Warn', '9'],
        ['3.20', 'Humidity.Category', '14', '', '0', '80', '80'],
        ['3.21', 'Dew Point.DescName', '1', '', '0', 'Dew Point', '0'],
        [
            '3.22', 'Dew Point.Value', '2', 'degree C', '-100',
            '-7.80 degree C', '-780'
        ], ['4.1', 'Smoke.DescName', '1', '', '0', 'Rauchmelder', '0'],
        ['4.2', 'Smoke.Value', '2', '', '1', '0', '0'],
        ['4.3', 'Smoke.Delay', '21', 's', '1', '0 s', '0'],
        ['4.4', 'Smoke.Status', '7', '', '0', 'OK', '4'],
        ['4.5', 'Smoke.Category', '14', '', '0', '80', '80']
    ]
]

discovery = {
    '': [
        ('CMC-IOModul', None), ('CMC-PU', None),
        ('CMC-Rauchmelder', None), ('CMC-Temperatur', None)
    ],
    'sensor': [],
    'psm_current': [],
    'psm_plugs': [],
    'io': [
        ('CMC-IOModul Input 1', {}), ('CMC-IOModul Input 2', {}),
        ('CMC-IOModul Input 3', {}), ('CMC-IOModul Input 4', {}),
        ('CMC-IOModul Input 5', {}), ('CMC-IOModul Input 6', {}),
        ('CMC-IOModul Input 7', {}), ('CMC-IOModul Input 8', {}),
        ('CMC-IOModul Output 1', {}), ('CMC-IOModul Output 2', {}),
        ('CMC-IOModul Output 3', {}), ('CMC-IOModul Output 4', {}),
        ('CMC-PU Input 1', {}), ('CMC-PU Input 2', {}),
        ('CMC-PU Output', {})
    ],
    'access': [('CMC-PU Access', None)],
    'temp': [
        ('Ambient CMC-PU', {}), ('Ambient CMC-Temperatur', {}),
        ('Dew Point CMC-Temperatur', {}), ('System CMC-PU', {})
    ],
    'temp_in_out': [],
    'can_current': [
        ('CMC-PU System.CAN1 Current', None),
        ('CMC-PU System.CAN2 Current', None)
    ],
    'humidity': [('CMC-Temperatur Humidity', {})],
    'phase': []
}

checks = {
    '': [
        ('CMC-IOModul', {}, [(0, 'Status: OK', [])]),
        ('CMC-PU', {}, [(0, 'Status: OK', [])]),
        ('CMC-Rauchmelder', {}, [(0, 'Status: OK', [])]),
        ('CMC-Temperatur', {}, [(0, 'Status: OK', [])])
    ],
    'io': [
        (
            'CMC-IOModul Input 1', {}, [
                (0, 'Status: OK, Logic: 0:OK / 1:Alarm, Delay: 5.0 s', [])
            ]
        ),
        (
            'CMC-IOModul Input 2', {}, [
                (0, 'Status: OK, Logic: 0:OK / 1:Alarm, Delay: 5.0 s', [])
            ]
        ),
        (
            'CMC-IOModul Input 3', {}, [
                (0, 'Status: Off, Logic: 0:On / 1:Off, Delay: 5.0 s', [])
            ]
        ),
        (
            'CMC-IOModul Input 4', {}, [
                (0, 'Status: OK, Logic: 0:Alarm / 1:OK, Delay: 0.5 s', [])
            ]
        ),
        (
            'CMC-IOModul Input 5', {}, [
                (0, 'Status: OK, Logic: 0:Alarm / 1:OK, Delay: 0.5 s', [])
            ]
        ),
        (
            'CMC-IOModul Input 6', {}, [
                (0, 'Status: OK, Logic: 0:Alarm / 1:OK, Delay: 0.5 s', [])
            ]
        ),
        (
            'CMC-IOModul Input 7', {}, [
                (0, 'Status: Off, Logic: 0:Off / 1:On, Delay: 0.5 s', [])
            ]
        ),
        (
            'CMC-IOModul Input 8', {}, [
                (0, 'Status: Off, Logic: 0:Off / 1:On, Delay: 0.5 s', [])
            ]
        ),
        (
            'CMC-IOModul Output 1', {}, [
                (0, 'Status: OK, Logic: 0:OK / 1:Alarm, Relay: Off', [])
            ]
        ),
        (
            'CMC-IOModul Output 2', {}, [
                (0, 'Status: OK, Logic: 0:OK / 1:Alarm, Relay: Off', [])
            ]
        ),
        (
            'CMC-IOModul Output 3', {}, [
                (0, 'Status: OK, Logic: 0:OK / 1:Alarm, Relay: Off', [])
            ]
        ),
        (
            'CMC-IOModul Output 4', {}, [
                (0, 'Status: OK, Logic: 0:OK / 1:Alarm, Relay: Off', [])
            ]
        ),
        (
            'CMC-PU Input 1', {}, [
                (0, 'Status: Off, Logic: 0:Off / 1:On, Delay: 0.5 s', [])
            ]
        ),
        (
            'CMC-PU Input 2', {}, [
                (0, 'Status: Off, Logic: 0:Off / 1:On, Delay: 0.5 s', [])
            ]
        ),
        (
            'CMC-PU Output', {}, [
                (2, 'Status: Off, Logic: 0:Off / 1:On, Relay: Off', [])
            ]
        )
    ],
    'access': [
        (
            'CMC-PU Access', {}, [
                (2, 'Door: Inactive, Delay: 10 s, Sensitivity: 0.0', [])
            ]
        )
    ],
    'temp': [
        (
            'Ambient CMC-PU', {}, [
                (0, '30.5 °C', [('temp', 30.5, 40.0, 45.0, None, None)])
            ]
        ),
        (
            'Ambient CMC-Temperatur', {}, [
                (0, '27.0 °C', [('temp', 27.0, 35.0, 40.0, None, None)])
            ]
        ),
        (
            'Dew Point CMC-Temperatur', {}, [
                (0, '-7.8 °C', [('temp', -7.8, None, None, None, None)])
            ]
        ),
        (
            'System CMC-PU', {}, [
                (
                    0, '[Sys Temp] 32.3 °C', [
                        ('temp', 32.3, 70.0, 80.0, None, None)
                    ]
                )
            ]
        )
    ],
    'can_current': [
        (
            'CMC-PU System.CAN1 Current', {}, [
                (
                    0,
                    'Status: OK, Current: 0.0 mA (warn/crit at 700.0/900.0 mA)',
                    [('current', 0.0, 0.7, 0.9, None, None)]
                )
            ]
        ),
        (
            'CMC-PU System.CAN2 Current', {}, [
                (
                    0,
                    'Status: OK, Current: 0.0 mA (warn/crit at 700.0/900.0 mA)',
                    [('current', 0.0, 0.7, 0.9, None, None)]
                )
            ]
        )
    ],
    'humidity': [
        (
            'CMC-Temperatur Humidity', {'levels': (10, 12), 'levels_lower': (5, 1)}, [
                (2, 'Status: Low Warn', []),
                (0, '9.5%', [('humidity', 9.5, 10, 12, 0, 100)])
            ]
        )
    ]
}
