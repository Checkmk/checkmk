# -*- encoding: utf-8
# yapf: disable
checkname = 'tplink_poe_summary'

info = [[u'150']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (0, '15.00 Watt', [('power', 15.0)])
            ]
        )
    ]
}
