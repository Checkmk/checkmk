# -*- encoding: utf-8
# yapf: disable
checkname = 'storeonce_servicesets'

freeze_time = '2020-01-02 13:38:00'

info = [
    ['[1]'], ['ServiceSet ID', '1'], ['ServiceSet Name', 'Service Set 1'],
    ['ServiceSet Alias', 'SET1'], ['Serial Number', 'CZ25132LTD01'],
    ['Software Version', '3.18.7-1841.1'],
    ['Product Class', 'HPE StoreOnce 4700 Backup'],
    ['Deduplication Ratio', '16.626312639082'],
    ['ServiceSet Health Level', '1'], ['ServiceSet Health', 'OK'],
    ['ServiceSet Status', 'Running'], ['Replication Health Level', '1'],
    ['Replication Health', 'OK'], ['Replication Status', 'Running'],
    ['Overall Health Level', '1'], ['Overall Health', 'OK'],
    ['Overall Status', 'Running'], ['Housekeeping Health Level', '1'],
    ['Housekeeping Health', 'OK'], ['Housekeeping Status', 'Running'],
    ['Primary Node', 'hpcz25132ltd'], ['Secondary Node', 'None'],
    ['Active Node', 'hpcz25132ltd'], ['cloudCapacityBytes', '0'],
    ['cloudDiskBytes', '0'], ['cloudReadWriteLicensedDiskBytes', '0'],
    ['cloudFreeBytes', '0'], ['cloudUserBytes', '0'],
    ['localCapacityBytes', '75952808613643'],
    ['localDiskBytes', '49547481098312'], ['localFreeBytes', '21647101662987'],
    ['localUserBytes', '823791911219548'],
    ['combinedCapacityBytes', '75952808613643'],
    ['combinedDiskBytes', '49547481098312'],
    ['combinedFreeBytes', '21647101662987'],
    ['combinedUserBytes', '823791911219548']
]

discovery = {'': [('1', {})], 'capacity': [('1', {})]}

checks = {
    '': [
        (
            '1', {}, [
                (0, 'Alias: SET1', []),
                (0, 'Overall Status: Running, Overall Health: OK', [])
            ]
        )
    ],
    'capacity': [
        (
            '1', {}, [
                (
                    0,
                    '71.5% used (24.70 of 34.54 PB), trend: 0.00 B / 24 hours',
                    [
                        (
                            '1', 26516458472.0, 29669065864.704296,
                            33377699097.792336, 0, 37086332330.88037
                        ),
                        ('fs_size', 37086332330.88037, None, None, None, None),
                        ('growth', 0.0, None, None, None, None),
                        ('trend', 0, None, None, 0, 1545263847.1200154)
                    ]
                ), (0, 'Dedup ratio: 16.63', [])
            ]
        )
    ]
}
