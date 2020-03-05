#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'aws_glacier_limits'


info = [[u'[["number_of_vaults",',
         u'"Vaults",',
         u'1000,',
         u'0,',
         u'"ap-northeast-2"]]'],
        [u'[["number_of_vaults",',
         u'"Vaults",',
         u'1000,',
         u'0,',
         u'"ca-central-1"]]'],
        [u'[["number_of_vaults",',
         u'"Vaults",',
         u'1000,',
         u'2,',
         u'"eu-central-1"]]'],
        [u'[["number_of_vaults",', u'"Vaults",', u'1000,', u'0,', u'"us-east-1"]]']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'number_of_vaults': (None, 80.0, 90.0)},
                [(0,
                  'No levels reached',
                  [(u'aws_glacier_number_of_vaults', 0, None, None, None, None),
                   (u'aws_glacier_number_of_vaults', 0, None, None, None, None),
                   (u'aws_glacier_number_of_vaults', 2, None, None, None, None),
                   (u'aws_glacier_number_of_vaults', 0, None, None, None, None)]),
                 (0,
                  u'\nVaults: 0 (of max. 1000) (Region ap-northeast-2)\nVaults: 0 (of max. 1000) (Region ca-central-1)\nVaults: 0 (of max. 1000) (Region us-east-1)\nVaults: 2 (of max. 1000) (Region eu-central-1)',
                  [])])]}
