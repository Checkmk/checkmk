#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore



checkname = 'liebert_temp_fluid'


info = [
    ['Supply Fluid Temp Set Point 1', '18.0', 'deg C',
     'Supply Fluid Temp Set Point 2', '14', 'deg C',
     'Supply Fluid Over Temp Alarm Threshold', '22', 'deg C',
     'Supply Fluid Under Temp Warning Threshold', '0', 'deg C',
     'Supply Fluid Under Temp Alarm Threshold', '0', 'deg C',
     'Supply Fluid Over Temp Warning Threshold', '0', 'deg C'],
]



discovery = {
    '': [
        ('Supply Fluid Temp Set Point 1', {}),
        ('Supply Fluid Temp Set Point 2', {}),
    ],
}


checks = {
    '': [
        ('Supply Fluid Temp Set Point 1', {}, [
            (0, '18.0 \xb0C', [
                ('temp', 18.0, 22.0, 22.0, None, None),
            ]),
        ]),
    ],
}
