# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_fans'


info = [[u'Fan Speed', u'1.3', u'%']]


discovery = {'': [(u'Fan Speed', {})]}


checks = {
    '': [
        (u'Fan Speed', {'levels': (80, 90), 'levels_lower': (2, 1)}, [
            (1, u'1.30 % (warn/crit below 2.00 %/1.00 %)', [
                ('filehandler_perc', 1.3, 80, 90, None, None),
            ]),
        ]),
    ],
}
