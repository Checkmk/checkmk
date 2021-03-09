# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_maintenance'


info = [[u'Calculated Next Maintenance Month', u'9'],
        [u'Calculated Next Maintenance Year', u'2019']]


freeze_time = "2019-08-23T12:00:00"

discovery = {'': [(None, {})]}


checks = {
    '': [
        (None, {'levels': (10, 5)}, [
            (0, 'Next maintenance: 9/2019', []),
            (1, '7 d (warn/crit below 10 d/5 d)', []),
        ]),
    ],
}
