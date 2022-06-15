#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'azure_storageaccounts'

info = [
    ['Resource'],
    [
        '{"sku": {"tier": "Standard", "name": "Standard_LRS"}, "kind": "BlobStorage", "group":'
        ' "BurningMan", "name": "st0ragetestaccount", "tags": {"monitoring": "some value"},'
        ' "provider": "Microsoft.Storage", "subscription": "2fac104f-cb9c-461d-be57-037039662426",'
        ' "type": "Microsoft.Storage/storageAccounts", "id": "/subscriptions/2fac104f-cb9c-461d'
        '-be57-037039662426/resourceGroups/BurningMan/providers/Microsoft.Storage/storageAccounts'
        '/st0ragetestaccount", "location": "westeurope"}'
    ],
    ['metrics following', '7'],
    ['{"name": "UsedCapacity", "timestamp": "1544591820", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 3822551.0, "unit": "bytes"}'],
    ['{"name": "Ingress", "timestamp": "1544595420", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 31620.0, "unit": "bytes"}'],
    ['{"name": "Egress", "timestamp": "1544595420", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 237007090.0, "unit": "bytes"}'],
    ['{"name": "Transactions", "timestamp": "1544595420", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 62.0, "unit": "count"}'],
    ['{"name": "SuccessServerLatency", "timestamp": "1544595420", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 5624.0, "unit": "milli_seconds"}'],
    ['{"name": "SuccessE2ELatency", "timestamp": "1544595420", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 9584.0, "unit": "milli_seconds"}'],
    ['{"name": "Availability", "timestamp": "1544595420", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 6200.0, "unit": "percent"}'],
    ['Resource'],
    [
        '{"sku": {"tier": "Standard", "name": "Standard_LRS"}, "kind": "Storage", "group":'
        ' "Glastonbury", "name": "glastonburydiag381", "tags": {}, "provider":'
        ' "Microsoft.Storage", "subscription": "2fac104f-cb9c-461d-be57-037039662426",'
        ' "type": "Microsoft.Storage/storageAccounts", "id": "/subscriptions/2fac104f-cb9c'
        '-461d-be57-037039662426/resourceGroups/Glastonbury/providers/Microsoft.Storage'
        '/storageAccounts/glastonburydiag381", "location": "westeurope"}'
    ],
    ['metrics following', '7'],
    ['{"name": "UsedCapacity", "timestamp": "1544598780", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 10773519964.0, "unit": "bytes"}'],
    ['{"name": "Ingress", "timestamp": "1544602380", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 43202937.0, "unit": "bytes"}'],
    ['{"name": "Egress", "timestamp": "1544602380", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 5835881.0, "unit": "bytes"}'],
    ['{"name": "Transactions", "timestamp": "1544602380", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 1907.0, "unit": "count"}'],
    ['{"name": "SuccessServerLatency", "timestamp": "1544602380", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 20105.0, "unit": "milli_seconds"}'],
    ['{"name": "SuccessE2ELatency", "timestamp": "1544602380", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 37606.0, "unit": "milli_seconds"}'],
    ['{"name": "Availability", "timestamp": "1544602380", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 190700.0, "unit": "percent"}'],
]

_common_discovery = [(u'glastonburydiag381', {}), (u'st0ragetestaccount', {})]

MiB = 1024**2

discovery = {sub: _common_discovery for sub in ('', 'flow', 'performance')}

checks = {
    '': [
        (u'glastonburydiag381', {}, [
            (0, u'Kind: Storage', []),
            (0, 'Used capacity: 10.0 GiB', [('used_space', 10773519964, None, None, 0, None)]),
            (0, u'Location: westeurope', []),
        ]),
        (u'st0ragetestaccount', {
            'used_capacity_levels': (2 * MiB, 4 * MiB)
        }, [
            (0, u'Kind: BlobStorage', []),
            (1, 'Used capacity: 3.65 MiB (warn/crit at 2.00 MiB/4.00 MiB)',
             [('used_space', 3822551, 2 * MiB, 4 * MiB, 0, None)]),
            (0, u'Location: westeurope', []),
            (0, u'Monitoring: some value', []),
        ]),
    ],
    'flow': [(u'glastonburydiag381', {}, [
        (0, 'Ingress: 41.2 MiB', [('ingress', 43202937, None, None, 0, None)]),
        (0, 'Egress: 5.57 MiB', [('egress', 5835881, None, None, 0, None)]),
        (0, 'Transactions: 1907', [('transactions', 1907.0, None, None, 0, None)]),
    ]),
             (u'st0ragetestaccount', {
                 'egress_levels': (100 * MiB, 200 * MiB)
             }, [
                 (0, 'Ingress: 30.9 KiB', [('ingress', 31620, None, None, 0, None)]),
                 (2, 'Egress: 226 MiB (warn/crit at 100 MiB/200 MiB)', [
                     ('egress', 237007090, 100 * MiB, 200 * MiB, 0, None),
                 ]),
                 (0, 'Transactions: 62', [('transactions', 62.0, None, None, 0, None)]),
             ])],
    'performance': [
        (u'glastonburydiag381', {}, [
            (0, 'Success server latency: 20105 ms', [('server_latency', 20.105, None, None, 0,
                                                      None)]),
            (0, 'End-to-end server latency: 37606 ms', [('e2e_latency', 37.606, None, None, 0,
                                                         None)]),
            (0, 'Availability: 190700.00%', [('availability', 190700.0, None, None, 0, None)]),
        ]),
        (u'st0ragetestaccount', {}, [
            (0, 'Success server latency: 5624 ms', [('server_latency', 5.624, None, None, 0,
                                                     None)]),
            (0, 'End-to-end server latency: 9584 ms', [('e2e_latency', 9.584, None, None, 0,
                                                        None)]),
            (0, 'Availability: 6200.00%', [('availability', 6200.0, None, None, 0, None)]),
        ]),
    ],
}
