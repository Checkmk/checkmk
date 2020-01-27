# yapf: disable
checkname = 'esx_vsphere_vm'

freeze_time = "2019-06-22 14:37"

info = [
    ['snapshot.rootSnapshotList', '154', '1560322675', 'poweredOn', 'VM-Snapshot', '12.06.2019', '10:56', 'UTC+02:00']
]

discovery = {
    'cpu': [],
    'datastores': [],
    'guest_tools': [],
    'heartbeat': [],
    'mem_usage': [],
    'mounted_devices': [],
    'name': [],
    'running_on': [],
    'snapshots': [(None, {})]
}

checks = {
    'snapshots': [
        (None, {'age_oldest': (30, 3600)}, [
            (0, 'Count: 1', []),
            (0, 'Powered on: VM-Snapshot 12.06.2019 10:56 UTC+02:00'),
            (0, 'Latest: VM-Snapshot 12.06.2019 10:56 UTC+02:00 2019-06-12 08:57:55', []),
            (2, 'Age of oldest: 10 d (warn/crit at 30.0 s/60 m)', [
                ('age_oldest', 891545.0, 30, 3600, None, None),
            ]),
        ]),
    ],
}
