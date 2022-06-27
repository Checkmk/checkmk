#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'f5_bigip_vserver'


info = [
    [u'/Common/sight-seeing.wurmhole.univ', u'1', u'1', u'The virtual server is available', u'\xd4;xK',
     u'', u'', u'', u'', u'', u'', u'', u'', u'0', u''],
    [u'/Common/www.wurmhole.univ_HTTP2HTTPS', u'4', u'1', (u"The children pool member(s) either don't"
     u" have service checking enabled, or service check results are not available yet"),
     u'\xd4;xI', u'', u'', u'', u'', u'', u'', u'', u'42', u'0', u''],
    [u'/Common/sight-seeing.wurmhole.univ_HTTP2HTTPS', u'4', u'1', (u"The children pool member(s) either"
     u" don't have service checking enabled, or service check results are not available yet"),
     u'\xd4;xK', u'', u'', u'', u'', u'', u'', u'', u'', u'0', u''],
    [u'/Common/starfleet.space', u'4', u'', u"To infinity and beyond!", u'\xde\xca\xff\xed', u'', u'',
     u'', u'', u'42', u'32', u'', u'', u'0', u''],
]


discovery = {
    '': [
        (u'/Common/sight-seeing.wurmhole.univ', {}),
        (u'/Common/sight-seeing.wurmhole.univ_HTTP2HTTPS', {}),
        (u'/Common/www.wurmhole.univ_HTTP2HTTPS', {}),
        (u'/Common/starfleet.space', {}),
    ],
}


checks = {
    '': [
        (u'/Common/sight-seeing.wurmhole.univ_HTTP2HTTPS', {}, [
            (0, u'Virtual Server with IP 212.59.120.75 is enabled', []),
            (1, (u'State availability is unknown, Detail: The children pool member(s) either'
                 u' don\'t have service checking enabled, or service check results are not'
                 u' available yet'), []),
            (0, 'Client connections: 0', [('connections', 0, None, None, None, None)]),
        ]),
        (u'/Common/www.wurmhole.univ', {}, []),
        (u'/Common/www.wurmhole.univ_HTTP2HTTPS', {}, [
            (0, u'Virtual Server with IP 212.59.120.73 is enabled', []),
            (1, (u'State availability is unknown, Detail: The children pool member(s) either'
                 u' don\'t have service checking enabled, or service check results are not'
                 u' available yet'), []),
            (0, 'Client connections: 0', [
                ('connections', 0, None, None, None, None),
                ('connections_rate', 0, None, None, None, None),
            ]),
            (0, 'Connections rate: 0.00/sec', []),
        ]),
        (u'/Common/starfleet.space', {
            "if_in_octets": (-23, 42),
            "if_total_pkts_lower": (100, 200),
            "if_total_pkts": (300, 400),
        }, [
            (1, u'Virtual Server with IP 222.202.255.237 is in unknown state', []),
            (1, u'State availability is unknown, Detail: To infinity and beyond!', []),
            (0, 'Client connections: 0', [
                ('connections', 0, None, None, None, None),
                ('if_in_octets', 0.0, None, None, None, None),
                ('if_out_pkts', 0.0, None, None, None, None),
                ('if_total_octets', 0.0, None, None, None, None),
                ('if_total_pkts', 0.0, None, None, None, None),
            ]),
            (1, 'Incoming bytes: 0.00 B/s (warn/crit at -23.0 B/s/42.0 B/s)', []),
            (2, 'Total packets: 0.0/s (warn/crit below 100.0/s/200.0/s)', []),
        ]),
    ],
}
