#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'azure_virtualnetworkgateways'

info = [
    [u'Resource'],
    [
        u'{"group": "Glastonbury", "name": "MeinGateway", "location": "westeurope", "provider": "Microsoft.Network", "type": "Microsoft.Network/virtualNetworkGateways", "id": "/subscriptions/2fac104f-cb9c-461d-be57-037039662426/resourceGroups/Glastonbury/providers/Microsoft.Network/virtualNetworkGateways/MeinGateway", "subscription": "2fac104f-cb9c-461d-be57-037039662426"}'
    ],
    [u'metrics following', u'3'],
    ['{"filter": null, "unit": "bytes_per_second", "name": "AverageBandwidth", "interval_id": "PT1M", "timestamp": "1545049860", "interval": "0:01:00", "aggregation": "average", "value": 13729.0}'],
    ['{"name": "P2SBandwidth", "aggregation": "average", "value": 0.0, "unit": "bytes_per_second", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter": null}'],
    ['{"name": "P2SConnectionCount", "aggregation": "maximum", "value": 1.0, "unit": "count", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter":   null}'],
]

discovery = {'': [(u'MeinGateway', {})]}

checks = {
    '': [(u'MeinGateway', {}, [
        (0, 'Point-to-site connections: 1', [('connections', 1, None, None, 0, None)]),
        (0, 'Point-to-site bandwidth: 0.00 B/s', [('p2s_bandwidth', 0.0, None, None, 0, None)]),
        (0, 'Site-to-site bandwidth: 13.7 kB/s', [('s2s_bandwidth', 13729.0, None, None, 0,
                                                    None)]),
        (0, u'Location: westeurope', []),
    ]),],
}
