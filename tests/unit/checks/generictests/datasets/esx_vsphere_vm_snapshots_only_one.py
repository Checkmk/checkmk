# yapf: disable
checkname = 'esx_vsphere_vm'

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
            (0, 'Number of Snapshots 1', []),
            (0, 'Powered On: VM-Snapshot 12.06.2019 10:56 UTC+02:00'),
            (0, 'Latest Snapshot: VM-Snapshot 12.06.2019 10:56 UTC+02:00 2019-06-12 08:57:55', []),
            # FIXME: Here should be a CRIT because the snapshot is old.
        ]),
    ],
}
