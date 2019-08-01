# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_bat_temp'


info = [
    [u'37'],
]



discovery = {
    '': [
        (u'Battery', "liebert_bat_temp_default"),
    ],
}


checks = {
    '': [
        (u'Battery', (30, 40), [
            (1, u'37 \xb0C (warn/crit at 30/40 \xb0C)', [
                ('temp', 37.0, 30.0, 40.0, None, None),
            ]),
        ]),
    ],
}
