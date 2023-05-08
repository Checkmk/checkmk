#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ibm_svc_mdisk'


info = [[u'id',
         u'status',
         u'mode',
         u'capacity',
         u'encrypt',
         u'enclosure_id',
         u'over_provisioned',
         u'supports_unmap',
         u'warning'],
        [u'0', u'online', u'array', u'20.8TB', u'no', u'1', u'no', u'yes', u'80']]


discovery = {'': []}
