# yapf: disable
checkname = 'systemd_units'

info = [
    ['[list-unit-files]'],
    ['[all]'],
    ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
    [
        'foo.service', 'loaded', 'failed', 'failed', 'Arbitrary', 'Executable', 'File', 'Formats',
        'File', 'System', 'Automount', 'Point'
    ],
    ['bar.service', 'loaded', 'failed', 'failed', 'a', 'bar', 'service'],
]

discovery = {'services': [], 'services_summary': [('Summary', {})]}

checks = {
    'services_summary': [('Summary', {
        'states': {
            'active': 0,
            'failed': 2,
            'inactive': 0
        },
        'states_default': 2,
        'else': 2
    }, [(0, '2 services in total', []), (2, '2 services failed (bar, foo)', [])])]
}
