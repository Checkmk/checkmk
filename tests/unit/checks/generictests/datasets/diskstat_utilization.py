# -*- encoding: utf-8
# yapf: disable
checkname = 'diskstat'

freeze_time = '2019-12-05 11:40:19'

parsed = {
    u'DM nvme0n1p3_crypt': {
        'node': None,
        'write_ios': 82.41379310344827,
        'read_ios': 3.6551724137931036,
        'average_wait': 0.0005336538461538461,
        'average_write_request_size': 8891.233472803347,
        'average_read_wait': 0.0007169811320754717,
        'latency': 0.0006057692307692308,
        'read_throughput': 22810.48275862069,
        'utilization': 0.05213793103448276,
        'write_throughput': 732760.275862069,
        'average_write_wait': 0.0005255230125523013,
        'queue_length': 0,
        'average_request_size': 8778.666666666666,
        'average_read_request_size': 6240.603773584905
    },
    u'LVM ubuntu--vg-swap_1': {
        'node': None,
        'write_ios': 0.0,
        'read_ios': 0.15517241379310345,
        'average_wait': 0.0,
        'average_write_request_size': 0.0,
        'average_read_wait': 0.0,
        'latency': 0.0017777777777777779,
        'read_throughput': 635.5862068965517,
        'utilization': 0.00027586206896551725,
        'write_throughput': 0.0,
        'average_write_wait': 0.0,
        'queue_length': 0,
        'average_request_size': 4096.0,
        'average_read_request_size': 0.0
    },
    u'LVM ubuntu--vg-root': {
        'node': None,
        'write_ios': 82.41379310344827,
        'read_ios': 3.5,
        'average_wait': 0.000536223158739715,
        'average_write_request_size': 8909.228451882846,
        'average_read_wait': 0.000748768472906404,
        'latency': 0.0006036524182219547,
        'read_throughput': 22174.896551724138,
        'utilization': 0.05186206896551724,
        'write_throughput': 734243.3103448276,
        'average_write_wait': 0.0005271966527196653,
        'queue_length': 0,
        'average_request_size': 8804.386112783464,
        'average_read_request_size': 6335.684729064039
    },
    u'nvme0n1': {
        'node': None,
        'write_ios': 72.87931034482759,
        'read_ios': 3.6379310344827585,
        'average_wait': 0.00012032447048219917,
        'average_write_request_size': 10054.43482375207,
        'average_read_wait': 0.0002938388625592417,
        'latency': 0.0006804867057232988,
        'read_throughput': 22810.48275862069,
        'utilization': 0.05206896551724138,
        'write_throughput': 732760.275862069,
        'average_write_wait': 0.00011166311805062691,
        'queue_length': 0,
        'average_request_size': 9874.516448850833,
        'average_read_request_size': 6270.18009478673
    }
}

discovery = {'': [('SUMMARY', 'diskstat_default_levels')]}

checks = {
    '': [
        (
            'SUMMARY', {}, [
                (
                    0, 'Utilization: 5.21%', [
                        (
                            'disk_utilization', 0.05210344827586207, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Read: 44.55 kB/s', [
                        (
                            'disk_read_throughput', 45620.96551724138, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Write: 1.40 MB/s', [
                        (
                            'disk_write_throughput', 1465520.551724138, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Average Wait: 0.33 ms', [
                        (
                            'disk_average_wait', 0.00032698915831802267, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Average Read Wait: 0.51 ms', [
                        (
                            'disk_average_read_wait', 0.0005054099973173567,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, 'Average Write Wait: 0.32 ms', [
                        (
                            'disk_average_write_wait', 0.0003185930653014641,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, 'Latency: 0.64 ms', [
                        (
                            'disk_latency', 0.0006431279682462648, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Average Queue Length: 0.00', [
                        ('disk_queue_length', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read operations: 7.29 1/s', [
                        (
                            'disk_read_ios', 7.293103448275862, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Write operations: 155.29 1/s', [
                        (
                            'disk_write_ios', 155.29310344827587, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, '', [
                        (
                            'disk_average_read_request_size',
                            6255.391934185817, None, None, None, None
                        ),
                        (
                            'disk_average_request_size', 9326.59155775875,
                            None, None, None, None
                        ),
                        (
                            'disk_average_write_request_size',
                            9472.834148277709, None, None, None, None
                        )
                    ]
                )
            ]
        )
    ]
}

extra_sections = {'': [[]]}
