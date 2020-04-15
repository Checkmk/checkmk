#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ibm_imm_health'


info = [[u'223523'],
        [u'2342'],
        [u'234'],
        [u'23352']]


discovery = {'': [(None, None)]}


checks = {'': [(None, {}, [(3, u'23352(234)', [])])]}
