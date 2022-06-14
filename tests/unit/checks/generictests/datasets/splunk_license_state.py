#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'splunk_license_state'


freeze_time = '2019-05-05T12:00:00'


info = [[u'license_state'],
        [u'Splunk_Enterprise_Splunk_Analytics_for_Hadoop_Download_Trial',
         u'5',
         u'30',
         u'524288000',
         u'1561977130',
         u'VALID'],
        [u'Splunk_Forwarder', u'5', u'30', u'1048576', u'2147483647', u'VALID'],
        [u'Splunk_Free', u'3', u'30', u'524288000', u'2147483647', u'VALID']]


discovery = {'': [(u'Splunk_Enterprise_Splunk_Analytics_for_Hadoop_Download_Trial', {}),
                  (u'Splunk_Forwarder', {}),
                  (u'Splunk_Free', {})]}


checks = {'': [(u'Splunk_Enterprise_Splunk_Analytics_for_Hadoop_Download_Trial',
                {'expiration_time': (1209600, 604800), 'state': 2},
                [(0, u'Status: VALID', []),
                 (0, 'Expiration time: 2019-07-01 12:32:10', []),
                 (0,
                  u'Max violations: 5 within window period of 30 Days, Quota: 500 MiB',
                  [])]),
               (u'Splunk_Forwarder',
                {'expiration_time': (1209600, 604800), 'state': 2},
                [(0, u'Status: VALID', []),
                 (0, 'Expiration time: 2038-01-19 04:14:07', []),
                 (0,
                  u'Max violations: 5 within window period of 30 Days, Quota: 1.00 MiB',
                  [])]),
               (u'Splunk_Free',
                {'expiration_time': (1209600, 604800), 'state': 2},
                [(0, u'Status: VALID', []),
                 (0, 'Expiration time: 2038-01-19 04:14:07', []),
                 (0,
                  u'Max violations: 3 within window period of 30 Days, Quota: 500 MiB',
                  [])])]}
