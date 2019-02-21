# yapf: disable
checkname = 'azure_virtualnetworkgateways'

info = [
    [u'Resource'],
    [
        u'{"group": "Glastonbury", "name": "MeinGateway", "location": "westeurope", "provider": "Microsoft.Network", "type": "Microsoft.Network/virtualNetworkGateways", "id": "/subscriptions/2fac104f-cb9c-461d-be57-037039662426/resourceGroups/Glastonbury/providers/Microsoft.Network/virtualNetworkGateways/MeinGateway", "subscription": "2fac104f-cb9c-461d-be57-037039662426"}'
    ],
    [u'metrics following', u'3'],
    [u'name', u'aggregation', u'value', u'unit', u'timestamp', u'timegrain', u'filters'],
    [
        u'AverageBandwidth', u'average', u'13729.0', u'bytes_per_second', u'1545049860', u'PT1M',
        u'None'
    ],
    [u'P2SBandwidth', u'average', u'0.0', u'bytes_per_second', u'1545050040', u'PT1M', u'None'],
    [u'P2SConnectionCount', u'maximum', u'1.0', u'count', u'1545050040', u'PT1M', u'None'],
]

discovery = {'': [(u'MeinGateway', {})]}

checks = {
    '': [(u'MeinGateway', {}, [
        (0, 'Point-to-site connections: 1', [('connections', 1, None, None, 0, None)]),
        (0, 'Point-to-site bandwidth: 0.00 B/s', [('p2s_bandwidth', 0.0, None, None, 0, None)]),
        (0, 'Site-to-site bandwidth: 13.41 kB/s', [('s2s_bandwidth', 13729.0, None, None, 0,
                                                    None)]),
        (0, u'Location: westeurope', []),
    ]),],
}
