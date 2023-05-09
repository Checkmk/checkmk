#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ibm_svc_node'


info = [[u'1',
         u'N1_164191',
         u'10001AA202',
         u'500507680100D7CA',
         u'online',
         u'0',
         u'io_grp0',
         u'no',
         u'2040000051442002',
         u'CG8  ',
         u'iqn.1986-03.com.ibm',
         u'2145.svc-cl.n1164191',
         u'',
         u'164191',
         u'',
         u'',
         u'',
         u'',
         u''],
        [u'2',
         u'N2_164373',
         u'10001AA259',
         u'500507680100D874',
         u'online',
         u'0',
         u'io_grp0',
         u'no',
         u'2040000051442149',
         u'CG8  ',
         u'iqn.1986-03.com.ibm',
         u'2145.svc-cl.n2164373',
         u'',
         u'164373',
         u'',
         u'',
         u'',
         u'',
         u''],
        [u'5',
         u'N3_162711',
         u'100025E317',
         u'500507680100D0A7',
         u'online',
         u'1',
         u'io_grp1',
         u'no',
         u'2040000085543047',
         u'CG8  ',
         u'iqn.1986-03.com.ibm',
         u'2145.svc-cl.n3162711',
         u'',
         u'162711',
         u'',
         u'',
         u'',
         u'',
         u''],
        [u'6',
         u'N4_164312',
         u'100025E315',
         u'500507680100D880',
         u'online',
         u'1',
         u'io_grp1',
         u'yes',
         u'2040000085543045',
         u'CG  8',
         u'iqn.1986-03.com.ibm',
         u'2145.svc-cl.n4164312',
         u'',
         u'164312',
         u'',
         u'',
         u'',
         u'',
         u'']]


discovery = {'': [(u'io_grp0', {}), (u'io_grp1', {})]}


checks = {'': [(u'io_grp0',
                {},
                [(0, u'Node N1_164191 is online, Node N2_164373 is online', [])]),
               (u'io_grp1',
                {},
                [(0, u'Node N3_162711 is online, Node N4_164312 is online', [])])]}
