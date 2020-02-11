# -*- encoding: utf-8
# yapf: disable
checkname = 'tplink_cpu'

info = [[u'21']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (0, 'Total CPU: 21.0%', [('util', 21.0, None, None, 0, 100)])
            ]
        )
    ]
}
