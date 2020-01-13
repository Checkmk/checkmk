# -*- encoding: utf-8
# yapf: disable
checkname = 'cisco_mem'

info = [
    ['Processor', '27086628', '46835412', '29817596'],
    ['I/O', '12409052', '2271012', '2086880'],
    ['Driver text', '40', '1048536', '1048532']
]

discovery = {'': [('I/O', {}), ('Processor', {})]}

checks = {
    '': [
        (
            'I/O', {
                'levels': (80.0, 90.0)
            }, [
                (
                    1,
                    'Used (11.83 MB of 14.00 MB): 84.53% (warn/crit at 80.0%/90.0%)',
                    [('mem_used', 84.52995845249721, 80.0, 90.0, 0, 100)]
                )
            ]
        ),
        (
            'Processor', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used (25.83 MB of 70.50 MB): 36.64%', [
                        ('mem_used', 36.64215435612978, 80.0, 90.0, 0, 100)
                    ]
                )
            ]
        )
    ]
}
