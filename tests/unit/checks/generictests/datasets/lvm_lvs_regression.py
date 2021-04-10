#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'lvm_lvs'

info = [[
    u'mysql', u'VG-OL-data', u'Vwi-aotz--', u'31138512896', u'tp', u'',
    u'77.75', u'', u'', u'', u'', u''
],
        [
            u'onkostar', u'VG-OL-data', u'Vwi-aotz--', u'13958643712', u'tp',
            u'', u'99.99', u'', u'', u'', u'', u''
        ],
        [
            u'tp', u'VG-OL-data', u'twi-aotz--', u'53573844992', u'', u'',
            u'71.25', u'34.86', u'', u'', u'', u''
        ],
        [
            u'root', u'VG-OL-root', u'-wi-ao----', u'12884901888', u'', u'',
            u'', u'', u'', u'', u'', u''
        ],
        [
            u'swap', u'VG-OL-swap', u'-wi-ao----', u'8585740288', u'', u'',
            u'', u'', u'', u'', u'', u''
        ]]

discovery = {'': [(u'VG-OL-data/tp', {})]}

checks = {
    '': [(
        u'VG-OL-data/tp',
        {
            'levels_data': (80.0, 90.0),
            'levels_meta': (80.0, 90.0)
        },
        [
            (0, 'Data usage: 71.25%', [('data_usage', 71.25, 80.0, 90.0, None, None)]),
            (0, 'Meta usage: 34.86%', [('meta_usage', 34.86, 80.0, 90.0, None, None)]),
        ],
    )]
}
