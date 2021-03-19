#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'printer_supply'

info = [
    [['1.1', 'black'], ['1.2', 'cyan'], ['1.3', 'magenta'], ['1.4', 'yellow'], ['1.5', 'very deep black']],
    [['Toner Cartridge OKI DATA CORP', '19', '100', '30', 'class', '1'],
    ['Toner Cartridge OKI DATA CORP', '19', '100', '10', 'class', '2'],
    ['Toner Cartridge OKI DATA CORP', '19', '100', '10', 'class', '3'],
    ['Toner Cartridge OKI DATA CORP', '19', '100', '40', 'class', '4'],
    ['Image Drum Unit OKI DATA CORP', '1', '20000', '409', 'class', '0'],
    ['Image Drum Unit OKI DATA CORP', '1', '20000', '7969', 'class', '0'],
    ['Image Drum Unit OKI DATA CORP', '1', '20000', '11597', 'class', '0'],
    ['Image Drum Unit OKI DATA CORP', '1', '20000', '4621', 'class', '0'],
    ['Belt Unit OKI DATA CORP', '2', '60000', '47371', 'class', '0'],
    ['Fuser Unit OKI DATA CORP', '2', '60000', '26174', 'class', '0'],
    ['Waste Toner box OKI DATA CORP', '1', '1', '-2', 'class', '0'],
    ['ZFoobar', '15', '4615', '4615', '3', '5']]
]

discovery = {
    '': [
        ('Belt Unit OKI DATA CORP', {}),
        ('Black Image Drum Unit OKI DATA CORP', {}),
        ('Black Toner Cartridge OKI DATA CORP', {}),
        ('Cyan Image Drum Unit OKI DATA CORP', {}),
        ('Cyan Toner Cartridge OKI DATA CORP', {}),
        ('Fuser Unit OKI DATA CORP', {}),
        ('Magenta Image Drum Unit OKI DATA CORP', {}),
        ('Magenta Toner Cartridge OKI DATA CORP', {}),
        ('Waste Toner box OKI DATA CORP', {}),
        ('Yellow Image Drum Unit OKI DATA CORP', {}),
        ('Yellow Toner Cartridge OKI DATA CORP', {}), ('ZFoobar', {})
    ]
}

checks = {
    '': [
        (
            'Belt Unit OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [
                (
                    0, 'Remaining: 79%, Supply: 47371 of max. 60000', [
                        ('pages', 47371, 12000.0, 6000.0, 0, 60000)
                    ]
                )
            ]
        ),
        (
            'Black Image Drum Unit OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [
                (
                    2,
                    'Remaining: 2% (warn/crit at 20%/10%), Supply: 409 of max. 20000',
                    [('pages', 409, 4000.0, 2000.0, 0, 20000)]
                )
            ]
        ),
        (
            'Black Toner Cartridge OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [
                (
                    0, 'Remaining: 30%, Supply: 30 of max. 100%', [
                        ('pages', 30, 20.0, 10.0, 0, 100)
                    ]
                )
            ]
        ),
        (
            'Cyan Image Drum Unit OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [
                (
                    0, 'Remaining: 40%, Supply: 7969 of max. 20000', [
                        ('pages', 7969, 4000.0, 2000.0, 0, 20000)
                    ]
                )
            ]
        ),
        (
            'Cyan Toner Cartridge OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [
                (
                    2,
                    'Remaining: 10% (warn/crit at 20%/10%), Supply: 10 of max. 100%',
                    [('pages', 10, 20.0, 10.0, 0, 100)]
                )
            ]
        ),
        (
            'Fuser Unit OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [
                (
                    0, 'Remaining: 44%, Supply: 26174 of max. 60000', [
                        ('pages', 26174, 12000.0, 6000.0, 0, 60000)
                    ]
                )
            ]
        ),
        (
            'Magenta Image Drum Unit OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [
                (
                    0, 'Remaining: 58%, Supply: 11597 of max. 20000', [
                        ('pages', 11597, 4000.0, 2000.0, 0, 20000)
                    ]
                )
            ]
        ),
        (
            'Magenta Toner Cartridge OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [
                (
                    2,
                    'Remaining: 10% (warn/crit at 20%/10%), Supply: 10 of max. 100%',
                    [('pages', 10, 20.0, 10.0, 0, 100)]
                )
            ]
        ),
        (
            'Waste Toner box OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [(3, ' Unknown level', [])]
        ),
        (
            'Yellow Image Drum Unit OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [
                (
                    0, 'Remaining: 23%, Supply: 4621 of max. 20000', [
                        ('pages', 4621, 4000.0, 2000.0, 0, 20000)
                    ]
                )
            ]
        ),
        (
            'Yellow Toner Cartridge OKI DATA CORP', {
                'levels': (20.0, 10.0)
            }, [
                (
                    0, 'Remaining: 40%, Supply: 40 of max. 100%', [
                        ('pages', 40, 20.0, 10.0, 0, 100)
                    ]
                )
            ]
        ),
        (
            'ZFoobar', {
                'levels': (20.0, 10.0)
            }, [
                (
                    0,
                    '[very deep black] Remaining: 100%, Supply: 4615 of max. 4615 tenths of milliliters',
                    [('pages', 4615, 923.0, 461.5, 0, 4615)]
                )
            ]
        )
    ]
}
