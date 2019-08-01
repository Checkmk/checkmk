# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_fans_condenser'


info = [[u'How funny is this', u'4.2', u'out of 10 clowns']]


discovery = {'': [(u'How funny is this', {})]}


checks = {
    '': [
        (u'How funny is this', {'levels_lower': (8, 9), 'levels': (80, 90)}, [
            (2, u'4.20 out of 10 clowns (warn/crit below 8.00 out of 10 clowns/9.00 out of 10 clowns)', [
                ('filehandler_perc', 4.2, 80, 90, None, None),
            ]),
        ]),
    ],
}
