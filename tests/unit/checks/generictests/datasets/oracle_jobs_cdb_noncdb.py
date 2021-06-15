#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'oracle_jobs'

info = [
          [u'CDB',
           u'CDB$ROOT',
           u'SYS',
           u'AUTO_SPACE_ADVISOR_JOB',
           u'SCHEDULED',
           u'0',
           u'46',
           u'TRUE',
           u'15-JUN-21 01.01.01.143871 AM +00:00',
           u'-',
           u'SUCCEEDED'],
          [u'NONCDB',
           u'SYS',
           u'AUTO_SPACE_ADVISOR_JOB',
           u'SCHEDULED',
           u'995',
           u'1129',
           u'TRUE',
           u'16-JUN-21 01.01.01.143871 AM +00:00',
           u'MAINTENANCE_WINDOW_GROUP',
           u''],

]

discovery = {
    '': [
      ('CDB.CDB$ROOT.SYS.AUTO_SPACE_ADVISOR_JOB', {}),
      ('NONCDB.SYS.AUTO_SPACE_ADVISOR_JOB', {})
    ]
}

checks = {
    '': [
        (
            'CDB.CDB$ROOT.SYS.AUTO_SPACE_ADVISOR_JOB', {
                'disabled': False,
                'status_missing_jobs': 2,
                'missinglog': 0
            }, [
                (
                    0,
                    'Job-State: SCHEDULED, Enabled: Yes, Last Duration: 0.00 s, Next Run: 15-JUN-21 01.01.01.143871 AM +00:00, Last Run Status: SUCCEEDED (ignored disabled Job)',
                    [('duration', 0, None, None, None, None)]
                )
            ]
        ),


        (
            'NONCDB.SYS.AUTO_SPACE_ADVISOR_JOB', {
                'disabled': False,
                'status_missing_jobs': 2,
                'missinglog': 1
            }, [
                (
                    1,
                    'Job-State: SCHEDULED, Enabled: Yes, Last Duration: 16 m, Next Run: 16-JUN-21 01.01.01.143871 AM +00:00,  no log information found(!)',
                    [('duration', 995, None, None, None, None)]
                )
            ]
        )
    ]
}
