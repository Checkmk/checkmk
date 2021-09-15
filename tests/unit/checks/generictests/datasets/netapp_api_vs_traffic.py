#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'netapp_api_vs_traffic'

freeze_time = '2001-09-09T01:46:40'

mock_item_state = {
    '': {
        'cifs:vserver.cifs_read_latency': (20000, 1000),
        'cifs:vserver.cifs_read_ops': (20000, 1000),
        'cifs:vserver.cifs_write_latency': (20000, 1000),
        'cifs:vserver.cifs_write_ops': (20000, 1000),
        'fcp_lif:vserver.fcp_read_latency': (20000, 1000),
        'fcp_lif:vserver.fcp_write_latency': (20000, 1000),
        'fcp_lif:vserver.read_data': (20000, 1000),
        'fcp_lif:vserver.write_data': (20000, 1000),
        'iscsi_lif:vserver.iscsi_read_latency': (20000, 1000),
        'iscsi_lif:vserver.iscsi_write_latency': (20000, 1000),
        'iscsi_lif:vserver.read_data': (20000, 1000),
        'iscsi_lif:vserver.write_data': (20000, 1000),
        'lif:vserver.recv_data': (20000, 1000),
        'lif:vserver.recv_errors': (20000, 1000),
        'lif:vserver.recv_packet': (20000, 1000),
        'lif:vserver.sent_data': (20000, 1000),
        'lif:vserver.sent_errors': (20000, 1000),
        'lif:vserver.sent_packet': (20000, 1000),
        'nfsv3.nfsv3_ops': (20000, 1000),
        'nfsv3.nfsv3_read_ops': (20000, 1000),
        'nfsv3.nfsv3_read_throughput': (20000, 1000),
        'nfsv3.nfsv3_write_ops': (20000, 1000),
        'nfsv3.nfsv3_write_throughput': (20000, 1000),
        'nfsv4.nfs4_read_throughput': (20000, 1000),
        'nfsv4.nfs4_write_throughput': (20000, 1000),
        'nfsv4.nfsv4_ops': (20000, 1000),
        'nfsv4.nfsv4_read_ops': (20000, 1000),
        'nfsv4.nfsv4_write_ops': (20000, 1000),
        'nfsv4_1.nfs41_read_throughput': (20000, 1000),
        'nfsv4_1.nfs41_write_throughput': (20000, 1000),
        'nfsv4_1.nfsv4_1_ops': (20000, 1000)
    }
}


info = [
    [
        'protocol lif:vserver', 'instance_name lvs0', 'recv_data 10000',
        'sent_data 10000', 'recv_errors 10000', 'sent_errors 10000',
        'recv_packet 10000', 'sent_packet 10000'
    ],
    [
        'protocol fcp_lif:vserver', 'instance_name flvs0',
        'fcp_read_latency 10000', 'fcp_write_latency 10000', 'fcp_read_ops 10',
        'fcp_write_ops 10', 'read_data 10000', 'write_data 10000'
    ],
    [
        'protocol fcp_lif:vserver', 'instance_name flvs0_norefs',
        'fcp_read_latency 10000', 'fcp_write_latency 10000', 'read_data 10000',
        'write_data 10000'
    ],
    [
        'protocol cifs:vserver', 'instance_name pcvs0',
        'cifs_read_latency 10000', 'cifs_write_latency 10000',
        'cifs_read_ops 10000', 'cifs_write_ops 10000'
    ],
    [
        'protocol cifs:vserver', 'instance_name pcvs0_norefs',
        'cifs_read_latency 10000', 'cifs_write_latency 10000'
    ],
    [
        'protocol iscsi_lif:vserver', 'instance_name ilvs0',
        'iscsi_read_latency 10000', 'iscsi_write_latency 10000',
        'iscsi_read_ops 10', 'iscsi_write_ops 10', 'read_data 10000',
        'write_data 10000'
    ],
    [
        'protocol iscsi_lif:vserver', 'instance_name ilvs0_norefs',
        'iscsi_read_latency 10000', 'iscsi_write_latency 10000',
        'read_data 10000', 'write_data 10000'
    ],
    [
        'protocol nfsv3', 'instance_name n3', 'nfsv3_read_ops 10000',
        'nfsv3_write_ops 10000', 'nfsv3_read_throughput 10000',
        'nfsv3_write_throughput 10000', 'nfsv3_ops 10000'
    ],
    [
        'protocol nfsv4', 'instance_name n4', 'nfsv4_read_ops 10000',
        'nfsv4_write_ops 10000', 'nfsv4_read_throughput 10000',
        'nfsv4_write_throughput 10000', 'nfsv4_ops 10000'
    ],
    [
        'protocol nfsv4_1', 'instance_name n41', 'nfs4_1_ops 10000',
        'nfs41_read_throughput 10000', 'nfs41_write_throughput 10000'
    ]
]


discovery = {
    '': [
        ('flvs0', {}), ('flvs0_norefs', {}),
        ('ilvs0', {}), ('ilvs0_norefs', {}), ('lvs0', {}), ('n3', {}),
        ('n4', {}), ('n41', {}), ('pcvs0', {}), ('pcvs0_norefs', {})
    ]
}


checks = {
    '': [
        (
            'flvs0', {}, [
                (0, 'FCP avg. Read latency: -', []),
                (0, 'FCP avg. Write latency: -', []),
                (
                    0, 'FCP read data: 0.00 B', [
                        (
                            'fcp_read_data', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'FCP write data: 0.00 B', [
                        (
                            'fcp_write_data', 9.000180003600072e-06, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            'flvs0_norefs', {}, [
                (0, 'FCP avg. Read latency: -', []),
                (0, 'FCP avg. Write latency: -', []),
                (
                    0, 'FCP read data: 0.00 B', [
                        (
                            'fcp_read_data', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'FCP write data: 0.00 B', [
                        (
                            'fcp_write_data', 9.000180003600072e-06, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            'ilvs0', {}, [
                (0, 'iSCSI avg. Read latency: -', []),
                (0, 'iSCSI avg. Write latency: -', []),
                (
                    0, 'iSCSI read data: 0.00 B', [
                        (
                            'iscsi_read_data', 9.000180003600072e-06, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'iSCSI write data: 0.00 B', [
                        (
                            'iscsi_write_data', 9.000180003600072e-06, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            'ilvs0_norefs', {}, [
                (0, 'iSCSI avg. Read latency: -', []),
                (0, 'iSCSI avg. Write latency: -', []),
                (
                    0, 'iSCSI read data: 0.00 B', [
                        (
                            'iscsi_read_data', 9.000180003600072e-06, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'iSCSI write data: 0.00 B', [
                        (
                            'iscsi_write_data', 9.000180003600072e-06, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            'lvs0', {}, [
                (
                    0, 'Ethernet received data: 0.00 B', [
                        (
                            'if_in_octets', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Ethernet sent data: 0.00 B', [
                        (
                            'if_out_octets', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Ethernet received errors: 0', [
                        (
                            'if_in_errors', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Ethernet sent errors: 0', [
                        (
                            'if_out_errors', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Ethernet received packets: 0', [
                        (
                            'if_in_pkts', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Ethernet sent packets: 0', [
                        (
                            'if_out_pkts', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'n3', {}, [
                (
                    0, 'NFS read OPs: 0', [
                        (
                            'nfs_read_ios', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'NFS write OPs: 0', [
                        (
                            'nfs_write_ios', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'NFS read throughput: 0.00 B/s', [
                        (
                            'nfs_read_throughput', 9.000180003600072e-06, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'NFS write throughput: 0.00 B/s', [
                        (
                            'nfs_write_throughput', 9.000180003600072e-06,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, 'NFS OPs: 0', [
                        (
                            'nfs_ios', 9.000180003600072e-06, None, None, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'n4', {}, [
                (
                    0, 'NFSv4 read OPs: 0', [
                        (
                            'nfsv4_read_ios', 9.000180003600072e-06, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'NFSv4 write OPs: 0', [
                        (
                            'nfsv4_write_ios', 9.000180003600072e-06, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'NFSv4 OPs: 0', [
                        (
                            'nfsv4_ios', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'n41', {}, [
                (
                    0, 'NFSv4.1 read throughput: 0.00 B/s', [
                        (
                            'nfsv4_1_read_throughput', 9.000180003600072e-06,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, 'NFSv4.1 write throughput: 0.00 B/s', [
                        (
                            'nfsv4_1_write_throughput', 9.000180003600072e-06,
                            None, None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            'pcvs0', {}, [
                (0, 'CIFS read latency: -', []),
                (0, 'CIFS write latency: -', []),
                (
                    0, 'CIFS read OPs: 0', [
                        (
                            'cifs_read_ios', 9.000180003600072e-06, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'CIFS write OPs: 0', [
                        (
                            'cifs_write_ios', 9.000180003600072e-06, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            'pcvs0_norefs', {}, [
                (0, 'CIFS read latency: -', []),
                (0, 'CIFS write latency: -', [])
            ]
        )
    ]
}
