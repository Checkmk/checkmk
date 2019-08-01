# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_pump'


info = [
    [u'Pump Hours', u'3423', u'hr'],
    [u'Pump Hours', u'1', u'hr'],
    [u'Pump Hours Threshold', u'32', u'hr'],
    [u'Pump Hours Threshold', u'32', u'hr'],
]


discovery = {
    '': [
        (u'Pump Hours', {}),
        (u'Pump Hours 2', {}),
    ],
}


checks = {
    '': [
        (u'Pump Hours', {}, [
            (2, u'3423.00 hr (warn/crit at 32.00 hr/32.00 hr)', []),
        ]),
    ],
}
