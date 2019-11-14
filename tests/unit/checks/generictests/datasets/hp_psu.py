# -*- encoding: utf-8
# yapf: disable
checkname = 'hp_psu'

info = [[u'1', u'3', u'25'], [u'2', u'3', u'23']]

discovery = {
    '': [(u'1', None), (u'2', None)],
    'temp': [(u'1', {}), (u'2', {})]
}

checks = {
    '': [(u'1', {}, [(0, 'Powered', [])]), (u'2', {}, [(0, 'Powered', [])])],
    'temp': [
        (
            u'1', {
                'levels': (70, 80)
            }, [(0, u'25 \xb0C', [('temp', 25, 70, 80, None, None)])]
        ),
        (
            u'2', {
                'levels': (70, 80)
            }, [(0, u'23 \xb0C', [('temp', 23, 70, 80, None, None)])]
        )
    ]
}
