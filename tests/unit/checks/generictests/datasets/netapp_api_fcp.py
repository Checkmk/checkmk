# -*- encoding: utf-8
# yapf: disable


checkname = 'netapp_api_fcp'


freeze_time = '2001-09-09T01:46:40'
# This corresponds to epoch 1000000000.0.


mock_item_state = {
    '': {
        'node0.avg_latency': (1000000000.0 - 100.0, 1000.0),
        'node0.avg_write_latency': (1000000000.0 - 100.0, 2000.0),
        'node0.avg_read_latency': (1000000000.0 - 100.0, 3000.0),
        'node0.write_bytes': (1000000000.0 - 100.0, 4000.0),
        'node0.read_bytes': (1000000000.0 - 100.0, 5000.0),
        'node0.read_ops': (1000000000.0 - 100.0, 6000),
        'node0.write_ops': (1000000000.0 - 100.0, 7000),
    }
}


info = [[u'instance_name node0',
         u'state online',
         u'port_wwpn de:ad:be:ef',
         u'data-link-rate 16',
         u'read_ops 20000',
         u'write_ops 20000',
         u'read_data 20000',
         u'write_data 20000',
         u'total_ops 20000',
         u'avg_latency 10000000',
         u'avg_read_latency 20000000',
         u'avg_write_latency 5000000']]


discovery = {'': [(u'node0', {'inv_speed': 16000000000, 'inv_state': u'online'})]}


checks = {'': [(u'node0',
                {'inv_speed': 16000000000, 'inv_state': u'online'},
                [(0, u'State: online', []),
                 (0, '16.00 Gbit/s', []),
                 (0, u'Address de:ad:be:ef', []),
                 (0, 'Read: 150.00', [('read_bytes', 150.0, None, None, None, None)]),
                 (0, 'Write: 160.00', [('write_bytes', 160.0, None, None, None, None)]),
                 (0, 'Read OPS: 140', [('read_ops', 140, None, None, None, None)]),
                 (0, 'Write OPS: 130', [('write_ops', 130, None, None, None, None)]),
                 (0,
                  'Latency: 90.00 ms',
                  [('avg_latency_latency', 90.0, None, None, None, None)]),
                 (0,
                  'Read Latency: 170.00 ms',
                  [('avg_read_latency_latency', 170.0, None, None, None, None)]),
                 (0,
                  'Write Latency: 30.00 ms',
                  [('avg_write_latency_latency', 30.0, None, None, None, None)])])]}
