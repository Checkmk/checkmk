# -*- encoding: utf-8
# yapf: disable


checkname = 'esx_vsphere_counters'


info = [
    ['disk.read', '', '11#12#13', 'kiloBytesPerSecond'],
    ['disk.numberReadAveraged', '', '110#140#150', 'number'],
    ['disk.write', '', '51#49#53', 'kiloBytesPerSecond'],
    ['disk.numberWriteAveraged', '', '11#102#5', 'number'],
    ['disk.deviceLatency', '', '700#900#23', 'millisecond']
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
            (0, 'Read: 12 kB/s', [
                ('disk_read_throughput', 12288.0, None, None, None, None),
            ]),
            (0, 'Write: 51 kB/s', [
                ('disk_write_throughput', 52224.0, None, None, None, None),
            ]),
            (0, 'Latency: 900.00 ms', [
                ('disk_latency', 0.9, None, None, None, None),
            ]),
            (0, 'Read operations: 133.33 1/s', [
                ('disk_read_ios', 133.33333333333334, None, None, None, None),
            ]),
            (0, 'Write operations: 39.33 1/s', [
                ('disk_write_ios', 39.333333333333336, None, None, None, None),
            ]),
        ]),
    ],
}
