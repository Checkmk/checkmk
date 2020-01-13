# -*- encoding: utf-8
# yapf: disable
checkname = 'storeonce_servicesets'

freeze_time = '2020-01-02 13:41:00'

info = [
    [u'[1]'], [u'ServiceSet ID', u'1'],
    [u'ServiceSet Name', u'', u'Service Set 1'],
    [u'ServiceSet Alias', u'SET1'], [u'Serial Number', u'CZ25132LTD01'],
    [u'Software Version', u'3.15.1-1636.1'],
    [u'Product Class', u'HPE StoreOnce 4700 Backup'],
    [u'Capacity in bytes', u'75952808613643'],
    [u'Free Space in bytes', u'53819324528395'],
    [u'User Data Stored in bytes', u'305835970141743'],
    [u'Size On Disk in bytes', u'19180587585836'],
    [u'Deduplication Ratio', u'15.945078260668'],
    [u'ServiceSet Health Level', u'1'], [u'ServiceSet Health', u'OK'],
    [u'ServiceSet Status', u'Running'], [u'Replication Health Level', u'1'],
    [u'Replication Health', u'OK'], [u'Replication Status', u'Running'],
    [u'Overall Health Level', u'1'], [u'Overall Health', u'OK'],
    [u'Overall Status', u'Running'], [u'Housekeeping Health Level', u'1'],
    [u'Housekeeping Health', u'OK'], [u'Housekeeping Status', u'Running'],
    [u'Primary Node', u'hpcz25132ltd'], [u'Secondary Node', u'None'],
    [u'Active Node', u'hpcz25132ltd']
]

discovery = {'': [(u'1', {})], 'capacity': [(u'1', {})]}

checks = {
    '': [
        (
            u'1', {}, [
                (0, u'Alias: SET1', []),
                (0, u'Overall Status: Running, Overall Health: OK', [])
            ]
        )
    ],
    'capacity': [
        (
            u'1', {}, [
                (
                    0,
                    '29.14% used (10.07 of 34.54 PB), trend: 0.00 B / 24 hours',
                    [
                        (
                            u'1', 10807365276.0, 29669065864.704296,
                            33377699097.792336, 0, 37086332330.88037
                        ),
                        ('fs_size', 37086332330.88037, None, None, None, None),
                        ('growth', 0.0, None, None, None, None),
                        ('trend', 0, None, None, 0, 1545263847.1200154)
                    ]
                ), (0, 'Dedup ratio: 15.95', [])
            ]
        )
    ]
}
