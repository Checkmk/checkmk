# -*- encoding: utf-8
# yapf: disable


checkname = 'esx_vsphere_counters'


info = [
    ['disk.read', '', '12', 'kiloBytesPerSecond'],
    ['disk.numberRead', '', '1', 'number'],
    ['disk.write', '', '51', 'kiloBytesPerSecond'],
    ['disk.numberWrite', '', '2', 'kiloBytesPerSecond'],
]


discovery = {
    '': [],
    'diskio': [
        ('SUMMARY', {}),
    ],
    'if': [],
    'ramdisk': [],
    'uptime': [],
}


checks = {
    'diskio': [
        ('SUMMARY', {}, [
            (0, 'Read: 12.00 kB/s', [
                ('disk_read_throughput', 12288.0, None, None, None, None),
            ]),
            (0, 'Write: 51.00 kB/s', [
                ('disk_write_throughput', 52224.0, None, None, None, None),
            ]),
            (0, 'Latency: 0.00 ms', [
                ('disk_latency', 0.0, None, None, None, None),
            ]),
            (0, 'Read operations: 1.00 1/s', [
                ('disk_read_ios', 1.0, None, None, None, None),
            ]),
            (0, 'Write operations: 2.00 1/s', [
                ('disk_write_ios', 2.0, None, None, None, None),
            ]),
        ]),
    ],
}
