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
    ['name', 'aggregation', 'value', 'unit', 'timestamp', 'timegrain', 'filters'],
    ['UsedCapacity', 'total', '3822551.0', 'bytes', '1544591820', 'PT1H', 'None'],
    ['Ingress', 'total', '31620.0', 'bytes', '1544595420', 'PT1H', 'None'],
    ['Egress', 'total', '237007090.0', 'bytes', '1544595420', 'PT1H', 'None'],
    ['Transactions', 'total', '62.0', 'count', '1544595420', 'PT1H', 'None'],
    ['SuccessServerLatency', 'total', '5624.0', 'milli_seconds', '1544595420', 'PT1H', 'None'],
    ['SuccessE2ELatency', 'total', '9584.0', 'milli_seconds', '1544595420', 'PT1H', 'None'],
    ['Availability', 'total', '6200.0', 'percent', '1544595420', 'PT1H', 'None'],
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
    ['name', 'aggregation', 'value', 'unit', 'timestamp', 'timegrain', 'filters'],
    ['UsedCapacity', 'total', '10773519964.0', 'bytes', '1544598780', 'PT1H', 'None'],
    ['Ingress', 'total', '43202937.0', 'bytes', '1544602380', 'PT1H', 'None'],
    ['Egress', 'total', '5835881.0', 'bytes', '1544602380', 'PT1H', 'None'],
    ['Transactions', 'total', '1907.0', 'count', '1544602380', 'PT1H', 'None'],
    ['SuccessServerLatency', 'total', '20105.0', 'milli_seconds', '1544602380', 'PT1H', 'None'],
    ['SuccessE2ELatency', 'total', '37606.0', 'milli_seconds', '1544602380', 'PT1H', 'None'],
    ['Availability', 'total', '190700.0', 'percent', '1544602380', 'PT1H', 'None'],
]

_common_discovery = [(u'glastonburydiag381', {}), (u'st0ragetestaccount', {})]

MB = 1024**2

discovery = {sub: _common_discovery for sub in ('', 'flow', 'performance')}

checks = {
    '': [
        (u'glastonburydiag381', {}, [
            (0, u'Kind: Storage', []),
            (0, 'Used capacity: 10.03 GB', [('used_space', 10773519964, None, None, 0, None)]),
            (0, u'Location: westeurope', []),
        ]),
        (u'st0ragetestaccount', {
            'used_capacity_levels': (2 * MB, 4 * MB)
        }, [
            (0, u'Kind: BlobStorage', []),
            (1, 'Used capacity: 3.65 MB (warn/crit at 2.00 MB/4.00 MB)',
             [('used_space', 3822551, 2 * MB, 4 * MB, 0, None)]),
            (0, u'Location: westeurope', []),
            (0, u'Monitoring: some value', []),
        ]),
    ],
    'flow': [(u'glastonburydiag381', {}, [
        (0, 'Ingress: 41.20 MB', [('ingress', 43202937, None, None, 0, None)]),
        (0, 'Egress: 5.57 MB', [('egress', 5835881, None, None, 0, None)]),
        (0, 'Transactions: 1907', [('transactions', 1907.0, None, None, 0, None)]),
    ]),
             (u'st0ragetestaccount', {
                 'egress_levels': (100 * MB, 200 * MB)
             }, [
                 (0, 'Ingress: 30.88 kB', [('ingress', 31620, None, None, 0, None)]),
                 (2, 'Egress: 226.03 MB (warn/crit at 100.00 MB/200.00 MB)', [
                     ('egress', 237007090, 100 * MB, 200 * MB, 0, None),
                 ]),
                 (0, 'Transactions: 62', [('transactions', 62.0, None, None, 0, None)]),
             ])],
    'performance': [
        (u'glastonburydiag381', {}, [
            (0, 'Success server latency: 20105 ms', [('server_latency', 20.105, None, None, 0,
                                                      None)]),
            (0, 'End-to-end server latency: 37606 ms', [('e2e_latency', 37.606, None, None, 0,
                                                         None)]),
            (0, 'Availability: 190700.0%', [('availability', 190700.0, None, None, 0, None)]),
        ]),
        (u'st0ragetestaccount', {}, [
            (0, 'Success server latency: 5624 ms', [('server_latency', 5.624, None, None, 0,
                                                     None)]),
            (0, 'End-to-end server latency: 9584 ms', [('e2e_latency', 9.584, None, None, 0,
                                                        None)]),
            (0, 'Availability: 6200.0%', [('availability', 6200.0, None, None, 0, None)]),
        ]),
    ],
}
