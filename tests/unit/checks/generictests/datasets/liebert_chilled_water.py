# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_chilled_water'


info = [[u'Supply Chilled Water Over Temp',
         u'Inactive Event',
         u'Chilled Water Control Valve Failure',
         u'Inactive Event',
         u'Supply Chilled Water Loss of Flow',
         u'Everything is on fire']]


discovery = {
    '': [
        (u'Supply Chilled Water Over Temp', {}),
        (u'Chilled Water Control Valve Failure', {}),
        (u'Supply Chilled Water Loss of Flow', {}),
    ],
}


checks = {
    '': [
        (u'Supply Chilled Water Over Temp', {}, [
            (0, u'Normal', []),
        ]),
        (u'Supply Chilled Water Loss of Flow', {}, [
            (2, u'Everything is on fire', []),
        ]),
    ],
}
