# -*- encoding: utf-8
# yapf: disable


checkname = 'docker_container_diskstat'


info = [
    ['node-1', '@docker_version_info', '{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.40"}'],
    ['node-1', ('{'
        '"io_service_time_recursive": ['
          '{"major": 8, "value": 1837047, "minor": 0, "op": "Read"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Write"}, '
          '{"major": 8, "value": 1837047, "minor": 0, "op": "Sync"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Async"}, '
          '{"major": 8, "value": 1837047, "minor": 0, "op": "Total"}], '
        '"sectors_recursive": ['
          '{"major": 8, "value": 24, "minor": 0, "op": ""}], '
        '"io_service_bytes_recursive": ['
          '{"major": 8, "value": 12288, "minor": 0, "op": "Read"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Write"}, '
          '{"major": 8, "value": 12288, "minor": 0, "op": "Sync"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Async"}, '
          '{"major": 8, "value": 12288, "minor": 0, "op": "Total"}, '
          '{"major": 8, "value": 12288, "minor": 0, "op": "Read"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Write"}, '
          '{"major": 8, "value": 12288, "minor": 0, "op": "Sync"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Async"}, '
          '{"major": 8, "value": 12288, "minor": 0, "op": "Total"}], '
        '"io_serviced_recursive": ['
          '{"major": 8, "value": 2, "minor": 0, "op": "Read"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Write"}, '
          '{"major": 8, "value": 2, "minor": 0, "op": "Sync"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Async"}, '
          '{"major": 8, "value": 2, "minor": 0, "op": "Total"}, '
          '{"major": 8, "value": 2, "minor": 0, "op": "Read"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Write"}, '
          '{"major": 8, "value": 2, "minor": 0, "op": "Sync"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Async"}, '
          '{"major": 8, "value": 2, "minor": 0, "op": "Total"}], '
        '"io_time_recursive": ['
          '{"major": 8, "value": 11196559, "minor": 0, "op": ""}], '
        '"names": {'
          '"8:0": "sda", "8:16": "sdb", "7:6": "loop6", "7:7": "loop7", "7:4": "loop4", '
          '"7:5": "loop5", "7:2": "loop2", "7:3": "loop3", "7:0": "loop0", "7:1": "loop1"}, '
        '"time": 1567584783.596914, '
        '"io_queue_recursive": ['
          '{"major": 8, "value": 0, "minor": 0, "op": "Read"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Write"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Sync"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Async"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Total"}], '
        '"io_merged_recursive": ['
          '{"major": 8, "value": 0, "minor": 0, "op": "Read"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Write"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Sync"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Async"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Total"}], '
        '"io_wait_time_recursive": ['
          '{"major": 8, "value": 25407, "minor": 0, "op": "Read"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Write"}, '
          '{"major": 8, "value": 25407, "minor": 0, "op": "Sync"}, '
          '{"major": 8, "value": 0, "minor": 0, "op": "Async"}, '
          '{"major": 8, "value": 25407, "minor": 0, "op": "Total"}]}'
    )],
]


discovery = {'': [('SUMMARY', 'diskstat_default_levels')]}


mock_item_state = {
    '': (1567584780, 0),
}


checks = {'': [('SUMMARY',
                {},
                [(0,
                  'Read: 3.34 kB/s',
                  [('disk_read_throughput', 3416.261778586769, None, None, None, None)]),
                 (0,
                  'Write: 0.00 B/s',
                  [('disk_write_throughput', 0.0, None, None, None, None)]),
                 (0,
                  'Read operations: 0.56 1/s',
                  [('disk_read_ios', 0.5560321905251903, None, None, None, None)]),
                 (0,
                  'Write operations: 0.00 1/s',
                  [('disk_write_ios', 0.0, None, None, None, None)])])]}
