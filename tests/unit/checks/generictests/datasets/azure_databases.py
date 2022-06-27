#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = "azure_databases"

info = [
    ['Resource'],
    [
        '{"sku": {"tier": "Basic", "capacity": 5, "name": "Basic"}, "kind":'
        ' "v12.0,user", "group": "Woodstock", "location": "westeurope", "provider":'
        ' "Microsoft.Sql", "subscription": "2fac104f-cb9c-461d-be57-037039662426", "type":'
        ' "Microsoft.Sql/servers/databases", "id": "/subscriptions/2fac104f-cb9c-461d-be57'
        '-037039662426/resourceGroups/Woodstock/providers/Microsoft.Sql/servers/hugo-server'
        '/databases/Testdatabase", "name": "hugo-server/Testdatabase"}'
    ],
    ['metrics following', '15'],
    ['{"name": "cpu_percent", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "percent"}'],
    ['{"name": "physical_data_read_percent", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "percent"}'],
    ['{"name": "log_write_percent", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "percent"}'],
    ['{"name": "dtu_consumption_percent", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "percent"}'],
    ['{"name": "storage", "timestamp": "1537538040", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 11403264.0, "unit": "bytes"}'],
    ['{"name": "connection_successful", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "connection_failed", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "blocked_by_firewall", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "deadlock", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "storage_percent", "timestamp": "1537538040", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 10.0, "unit": "percent"}'],
    ['{"name": "xtp_storage_percent", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "percent"}'],
    ['{"name": "workers_percent", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "percent"}'],
    ['{"name": "sessions_percent", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "percent"}'],
    ['{"name": "dtu_limit", "timestamp": "1537538040", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 5.0, "unit": "count"}'],
    ['{"name": "dtu_used", "timestamp": "1537538160", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
]

discovery = {
    '': [(u'hugo-server/Testdatabase', {})],
    'connections': [(u'hugo-server/Testdatabase', {})],
    'deadlock': [(u'hugo-server/Testdatabase', {})],
    'cpu': [(u'hugo-server/Testdatabase', {})],
    'dtu': [(u'hugo-server/Testdatabase', {})],
    'storage': [(u'hugo-server/Testdatabase', {})],
}

checks = {
    '': [(
        u'hugo-server/Testdatabase',
        {},
        [(0, u'Location: westeurope', [])],
    ),],
    'connections': [(u'hugo-server/Testdatabase', {}, [
        (0, 'Successful connections: 0', [('connections', 0, None, None, 0, None)]),
        (0, 'Rate of failed connections: 0.0', [('connections_failed_rate', 0.0, None, None, 0,
                                                 None)]),
    ]),],
    'deadlock': [(
        u'hugo-server/Testdatabase',
        {},
        [(0, 'Deadlocks: 0', [('deadlocks', 0, None, None, 0, None)])],
    ),],
    'dtu': [(
        u'hugo-server/Testdatabase',
        {
            'dtu_percent_levels': (85.0, 95.0)
        },
        [
            (0, 'Database throughput units: 0%', [('dtu_percent', 0.0, 85., 95., 0, None)]),
        ],
    )],
    'cpu': [(
        u'hugo-server/Testdatabase',
        {
            'cpu_percent_levels': (85.0, 95.0)
        },
        [
            (0, 'Total CPU: 0%', [('util', 0.0, 85., 95., 0, 100)]),
        ],
    )],
    'storage': [(u'hugo-server/Testdatabase', {
        'storage_percent_levels': (85.0, 95.0),
    }, [
        (0, 'Storage: 10.00% (10.9 MiB)', [('storage_percent', 10.0, 85., 95., 0, None)]),
    ]),],
}
