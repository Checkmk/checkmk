# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_reheating'


info = [[u'Reheating is awesome!', u'81.3', u'%'],
        [u'This value ignored', u'21.1', u'def C']]


discovery = {'': [(None, {})]}


checks = {
    '': [
        (None, {'levels': (80, 90)}, [
            (1, u'81.30 % (warn/crit at 80.00 %/90.00 %)', [
                ('filehandler_perc', 81.3, 80, 90, None, None),
            ]),
        ]),
    ],
}
