# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore


checkname = u'aws_ec2'

parsed = {
    'Summary': {
        'CPUUtilization': 0.1,
        'NetworkIn': 3540.4,
        'StatusCheckFailed_Instance': 0.0,
        'NetworkOut': 27942.1,
        'StatusCheckFailed_System': 0.0
    }
}

discovery = {
    '': [(None, {})],
    'cpu_util': [(None, {})],
    'network_io': [('Summary', {})],
    'disk_io': [],
    'cpu_credits': []
}

checks = {
    '': [(None, {}, [(0, 'System: passed', []), (0, 'Instance: passed', [])])],
    'cpu_util':
    [(None, {
        'util': (0.01, 95.0)
    }, [(1, 'Total CPU: 0.1% (warn/crit at 0.01%/95.0%)', [('util', 0.1, 0.01,
                                                            95.0, 0, 100)])]),
     (None, {
         'util': (90.0, 95.0)
     }, [(0, 'Total CPU: 0.1%', [('util', 0.1, 90.0, 95.0, 0, 100)])])],
    'network_io': [('Summary', {
        'errors_in': (0.01, 0.1),
        'errors_out': (0.01, 0.1)
    }, [(0, '[0] (up) speed unknown', [])])]
}
