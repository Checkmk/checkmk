# -*- encoding: utf-8
# yapf: disable


checkname = 'systemd_units'


info = [['[list-unit-files]'],
        ['[all]'],
        ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
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
        ['bar.service', 'loaded', 'failed', 'failed', 'a', 'bar', 'service']]


discovery = {'': [], 'services': [], 'services_summary': [('Summary', {})]}


checks = {'services_summary': [('Summary',
                                {'else': 2,
                                 'states': {'active': 0, 'failed': 2, 'inactive': 0},
                                 'states_default': 2},
                                [(0, '2 services in total', []),
                                 (2, '2 services failed (bar, foo)', [])])]}