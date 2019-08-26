# -*- encoding: utf-8
# yapf: disable


checkname = 'diskstat'


info = [[None, u'1565794757'],
        [None,
         u'202',
         u'2',
         u'xvda2',
         u'1183324',
         u'3073',
         u'74541194',
         u'4412672',
         u'44817791',
         u'33791401',
         u'2380487144',
         u'62094612',
         u'0',
         u'7709048',
         u'66546732'],
        [None,
         u'202',
         u'1',
         u'xvda1',
         u'66163',
         u'400791',
         u'3735632',
         u'122340',
         u'24816',
         u'653213',
         u'5424232',
         u'98180',
         u'0',
         u'102988',
         u'219916'],
        [None, u'[dmsetup_info]']]


discovery = {'': [('SUMMARY', 'diskstat_default_levels')]}


checks = {'': [('SUMMARY',
                {},
                [(0,
                  'Utilization: 0%',
                  [('disk_utilization', 0.0, None, None, None, None)]),
                 (0,
                  'Read: 0.00 B/s',
                  [('disk_read_throughput', 0.0, None, None, None, None)]),
                 (0,
                  'Write: 0.00 B/s',
                  [('disk_write_throughput', 0.0, None, None, None, None)]),
                 (0,
                  'Average Wait: 0.00 ms',
                  [('disk_average_wait', 0.0, None, None, None, None)]),
                 (0,
                  'Average Read Wait: 0.00 ms',
                  [('disk_average_read_wait', 0.0, None, None, None, None)]),
                 (0,
                  'Average Write Wait: 0.00 ms',
                  [('disk_average_write_wait', 0.0, None, None, None, None)]),
                 (0,
                  'Latency: 0.00 ms',
                  [('disk_latency', 0.0, None, None, None, None)]),
                 (0,
                  'Average Queue Length: 0.00',
                  [('disk_queue_length', 0.0, None, None, None, None)]),
                 (0,
                  'Read operations: 0.00 1/s',
                  [('disk_read_ios', 0.0, None, None, None, None)]),
                 (0,
                  'Write operations: 0.00 1/s',
                  [('disk_write_ios', 0.0, None, None, None, None)]),
                 (0,
                  '',
                  [('disk_average_read_request_size', 0.0, None, None, None, None),
                   ('disk_average_request_size', 0.0, None, None, None, None),
                   ('disk_average_write_request_size',
                    0.0,
                    None,
                    None,
                    None,
                    None)])])]}


extra_sections = {'': [[]]}