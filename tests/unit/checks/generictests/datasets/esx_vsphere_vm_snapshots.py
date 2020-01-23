# yapf: disable
checkname = 'esx_vsphere_vm'

info = [[
    'snapshot.rootSnapshotList', '1', '1363596734', 'poweredOff',
    '20130318_105600_snapshot_LinuxI|2', '1413977827', 'poweredOn', 'LinuxI', 'Testsnapshot'
]]

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
    'snapshots': [(None, {}, [
        (0, 'Count: 2', []),
        (0, 'Powered on: LinuxI Testsnapshot', []),
        (0, 'Latest: LinuxI Testsnapshot 2014-10-22 13:37:07', []),
        (0, 'Oldest: 20130318_105600_snapshot_LinuxI 2013-03-18 09:52:14', []),
    ]),]
}
