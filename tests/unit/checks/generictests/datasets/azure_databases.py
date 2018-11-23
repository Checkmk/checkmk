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
    ['name', 'aggregation', 'value', 'unit', 'timestamp', 'timegrain', 'filters'],
    ['cpu_percent', 'average', '0.0', 'percent', '1537538160', 'PT1M', 'None'],
    ['physical_data_read_percent', 'average', '0.0', 'percent', '1537538160', 'PT1M', 'None'],
    ['log_write_percent', 'average', '0.0', 'percent', '1537538160', 'PT1M', 'None'],
    ['dtu_consumption_percent', 'average', '0.0', 'percent', '1537538160', 'PT1M', 'None'],
    ['storage', 'average', '11403264.0', 'bytes', '1537538040', 'PT1M', 'None'],
    ['connection_successful', 'average', '0.0', 'count', '1537538160', 'PT1M', 'None'],
    ['connection_failed', 'average', '0.0', 'count', '1537538160', 'PT1M', 'None'],
    ['blocked_by_firewall', 'average', '0.0', 'count', '1537538160', 'PT1M', 'None'],
    ['deadlock', 'average', '0.0', 'count', '1537538160', 'PT1M', 'None'],
    ['storage_percent', 'average', '10.0', 'percent', '1537538040', 'PT1M', 'None'],
    ['xtp_storage_percent', 'average', '0.0', 'percent', '1537538160', 'PT1M', 'None'],
    ['workers_percent', 'average', '0.0', 'percent', '1537538160', 'PT1M', 'None'],
    ['sessions_percent', 'average', '0.0', 'percent', '1537538160', 'PT1M', 'None'],
    ['dtu_limit', 'average', '5.0', 'count', '1537538040', 'PT1M', 'None'],
    ['dtu_used', 'average', '0.0', 'count', '1537538160', 'PT1M', 'None'],
]

discovery = {
    ''           : [(u'hugo-server/Testdatabase', {})],
    'connections': [(u'hugo-server/Testdatabase', {})],
    'deadlock'   : [(u'hugo-server/Testdatabase', {})],
    'cpu'        : [(u'hugo-server/Testdatabase', {})],
    'dtu'        : [(u'hugo-server/Testdatabase', {})],
    'storage'    : [(u'hugo-server/Testdatabase', {})],
}

checks = {
    ''           : [(u'hugo-server/Testdatabase', 'default',
                       [(0, u'Location: westeurope', [])],
                    ),
                   ],
    'connections': [(u'hugo-server/Testdatabase', 'default',
                       [(0, 'Successful connections: 0', [('connections', 0, None, None, 0, None)]),
                        (0, 'Rate of failed connections: 0.0',
                            [('connections_failed_rate', 0.0, None, None, 0, None)]),
                       ]
                    ),
                   ],
    'deadlock'   : [(u'hugo-server/Testdatabase', 'default',
                       [(0, 'Deadlocks: 0', [('deadlocks', 0, None, None, 0, None)])],
                    ),
                   ],
    'dtu'        : [(u'hugo-server/Testdatabase', 'default',
                       [(0, 'Database throughput units: 0.0%', [('dtu_percent', 0.0, 85., 95., 0, None)]),
                       ],
                    )
                   ],
    'cpu'        : [(u'hugo-server/Testdatabase', 'default',
                       [(0, 'total cpu: 0.0%', [('util', 0.0, 85., 95., 0, 100)]),
                       ],
                    )
                   ],
    'storage'    : [(u'hugo-server/Testdatabase', 'default',
                       [(0, 'Storage: 10.0% (10.88 MB)',
                            [('storage_percent', 10.0, 85., 95., 0, None)]),
                       ]
                    ),
                   ],
}
