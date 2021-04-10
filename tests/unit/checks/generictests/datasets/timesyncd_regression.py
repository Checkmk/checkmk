#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'timesyncd'

freeze_time = '2019-10-02 07:34:59'

info = [[u'Server:', u'91.189.91.157', u'(ntp.ubuntu.com)'],
        [
            u'Poll', u'interval:', u'32s', u'(min:', u'32s;', u'max', u'34min',
            u'8s)'
        ], [u'Leap:', u'normal'], [u'Version:', u'4'], [u'Stratum:', u'2'],
        [u'Reference:', u'C0248F97'], [u'Precision:', u'1us', u'(-24)'],
        [u'Root', u'distance:', u'87.096ms', u'(max:', u'5s)'],
        [u'Offset:', u'-53.991ms'], [u'Delay:', u'208.839ms'],
        [u'Jitter:', u'0'], [u'Packet', u'count:', u'1'],
        [u'Frequency:', u'-500,000ppm'], [u'[[[1569922392.37]]]']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (None, {
            'alert_delay': (300, 3600),
            'last_synchronized': (5400, 7200),
            'quality_levels': (200.0, 500.0),
            'stratum_level': 10
         }, [
             (0, u'Offset: 54 microseconds', [('time_offset', 5.3991e-05, 0.2, 0.5)]),
             (2, ('Time since last sync: 22 hours 1 minute '
                 '(warn/crit at 1 hour 30 minutes/2 hours 0 minutes)'), []),
             (0, 'Stratum: 2.00', []),
             (0, 'Jitter: 0.00 s', [('jitter', 0.0, 0.2, 0.5)]),
             (0, u'synchronized on 91.189.91.157', []),
        ]),
    ],
}


# this should be set by the check itself, but that won't work in tests.
mock_item_state = {'': {'time_server': 1569922392.37}}
