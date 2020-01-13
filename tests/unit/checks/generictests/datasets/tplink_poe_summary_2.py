# -*- encoding: utf-8
# yapf: disable
checkname = 'tplink_poe_summary'

info = [[u'900']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, (90, 100), [
                (1, '90.00 Watt (warn/crit at 90.00 Watt/100.00 Watt)', [('power', 90.0, 90.0, 100.0)])
            ]
        )
    ]
}
