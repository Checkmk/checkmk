

checkname = 'systemd_units'


info = [['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
        ['foo.service',
         'loaded',
         'failed',
         'failed',
         'Arbitrary',
         'Executable',
         'File',
         'Formats',
         'File',
         'System',
         'Automount',
         'Point'],
        ['bar.service', 'loaded', 'failed', 'failed', 'a', 'bar', 'service'],
        ['2'],
        []]


discovery = {'services': [], 'services_summary': [('Summary', {})]}


checks = {'services_summary': [('Summary',
                                'default',
                                [(0, '2 services in total', []),
                                 (2, '2 services failed (foo, bar)', [])])]}
