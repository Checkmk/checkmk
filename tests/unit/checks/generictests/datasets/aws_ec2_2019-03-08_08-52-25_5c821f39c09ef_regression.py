# -*- encoding: utf-8
# yapf: disable


checkname = u'aws_ec2'


parsed = {'Summary': {'CPUUtilization': 0.1,
                      'NetworkIn': 3540.4,
                      'NetworkOut': 27942.1,
                      'StatusCheckFailed_Instance': 0.0,
                      'StatusCheckFailed_System': 0.0}}


discovery = {'': [(None, {})],
             'cpu_credits': [],
             'cpu_util': [(None, {})],
             'disk_io': [],
             'network_io': [('Summary', {})]}


checks = {'': [(None, {}, [(0, 'System: passed', []), (0, 'Instance: passed', [])])],
          'cpu_util': [(None,
                        {'levels': (90.0, 95.0)},
                        [(0, 'Total CPU: 0.1%', [('util', 0.1, 90.0, 95.0, 0, 100)])])],
          'network_io': [('Summary',
                          {'errors': (0.01, 0.1)},
                          [(0, '[0] (up) speed unknown', [])])]}