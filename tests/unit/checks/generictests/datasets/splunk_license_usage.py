#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'splunk_license_usage'


info = [[u'license_usage'], [u'524288000', u'5895880']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'usage_bytes': (80.0, 90.0)},
                [(0, 'Quota: 500 MiB', []),
                 (0,
                  'Slaves usage: 5.62 MiB',
                  [('splunk_slave_usage_bytes',
                    5895880,
                    419430400.0,
                    471859200.0,
                    None,
                    None)])])]}
