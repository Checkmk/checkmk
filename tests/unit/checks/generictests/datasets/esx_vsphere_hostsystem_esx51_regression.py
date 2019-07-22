# yapf: disable
checkname = 'esx_vsphere_hostsystem'

info = [
    [
        [
            # This is output from the old API endpoint for the check esx_vsphere_hostsystem.multipath
            # which is not supported anymore.
            u'config.multipathState.path',
            u'fc.20000024ff2e1b4c:21000024ff2e1b4c-fc.500a098088866d7e:500a098188866d7e-naa.60a9800044314f68553f436779684544',
            u'active',
        ],
        [u'hardware.cpuInfo.hz', u'2792999719'],
        [u'hardware.cpuInfo.numCpuCores', u'12'],
        [u'hardware.cpuInfo.numCpuPackages', u'2'],
        [u'hardware.cpuInfo.numCpuThreads', u'24'],
        [u'hardware.memorySize', u'309224034304'],
        [u'name', u'df1-esx03.roelfspartner.local'],
        [u'overallStatus', u'green'],
        [u'runtime.inMaintenanceMode', u'false'],
        [u'runtime.powerState', u'poweredOn'],
        [u'summary.quickStats.overallCpuUsage', u'1930'],
        [u'summary.quickStats.overallMemoryUsage', u'79464'],
    ],
    None,
]

discovery = {
    '': [],
    'cpu_usage': [(None, {})],
    'cpu_util_cluster': [],
    'maintenance': [(None, {
        'target_state': 'false'
    })],
    'mem_usage': [(None, 'esx_host_mem_default_levels')],
    'mem_usage_cluster': [],
    'multipath': [],
    'state': [(None, None)]
}

checks = {
    'cpu_usage': [(
        None,
        {},
        [(
            0,
            'Total CPU: 5.76%, 1.93GHz/33.52GHz, 2 sockets, 6 cores/socket, 24 threads',
            [('util', 5.758444307717932, None, None, 0, 100)],
        )],
    )],
    'maintenance': [(
        None,
        {
            'target_state': 'false'
        },
        [
            (0, 'System not in Maintenance mode', []),
        ],
    )],
    'mem_usage': [(
        None,
        (80.0, 90.0),
        [(
            0,
            '26% used - 77.60 GB/287.99 GB',
            [
                ('usage', 83324043264.0, 247379227443.2, 278301630873.6, 0, 309224034304.0),
                ('mem_total', 309224034304.0, None, None, None, None),
            ],
        )],
    )],
    'state': [(None, {}, [(0, 'Entity state: green', []), (0, 'Power state: poweredOn', [])])]
}
