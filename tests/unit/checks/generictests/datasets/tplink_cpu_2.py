# -*- encoding: utf-8
# yapf: disable
checkname = 'tplink_cpu'

info = [[u'100']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {'util': (90.0, 100.0)}, [
                (2, 'Total CPU: 100% (warn/crit at 90.0%/100%)', [('util', 100.0, 90.0, 100.0, 0, 100)])
            ]
        )
    ]
}
