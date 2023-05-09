#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'f5_bigip_vserver'


info = [[u'VS_BM',
         u'1',
         u'1',
         u'The virtual server is available',
         u'\xac\x14\xcad',
         u'38',
         u'76766',
         u'10744',
         u'70981',
         u'84431',
         u'10961763',
         u'83403367',
         u'2535',
         u'0',
         u'0'],
        ]


discovery = {'': [(u'VS_BM', {}),
                  ]}


checks = {'': [(u'VS_BM',
                {},
                [(0, 'Virtual Server with IP 172.20.202.100 is enabled', []),
                 (0,
                  u'State is up and available, Detail: The virtual server is available',
                  []),
                 (0,
                  'Client connections: 0',
                  [('connections', 0, None, None, None, None),
                   ('connections_duration_max', 76.766, None, None, None, None),
                   ('connections_duration_mean', 10.744, None, None, None, None),
                   ('connections_duration_min', 0.038, None, None, None, None),
                   ('connections_rate', 0.0, None, None, None, None),
                   ('if_in_octets', 0.0, None, None, None, None),
                   ('if_in_pkts', 0.0, None, None, None, None),
                   ('if_out_octets', 0.0, None, None, None, None),
                   ('if_out_pkts', 0.0, None, None, None, None),
                   ('if_total_octets', 0.0, None, None, None, None),
                   ('if_total_pkts', 0.0, None, None, None, None),
                   ('packet_velocity_asic', 0.0, None, None, None, None)]),
                 (0, 'Connections rate: 0.00/sec', [])]),
               ]}
