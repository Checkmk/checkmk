# -*- encoding: utf-8
# yapf: disable
checkname = 'tplink_mem'

info = [[u'50']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (0, 'Usage: 50.0%', [('mem_used_percent', 50.0)])
            ]
        )
    ]
}
