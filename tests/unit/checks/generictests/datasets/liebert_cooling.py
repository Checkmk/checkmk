# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_cooling'


info = [
    [u'Cooling Capacity (Primary)', u'42', u'%'],
    [u'Cooling Capacity (Secondary)', u'42', u'%'],
]


discovery = {
    '': [
        (u'Cooling Capacity (Primary)', {}),
        (u'Cooling Capacity (Secondary)', {}),
    ],
}


checks = {
    '': [
        (u'Cooling Capacity (Primary)', {"levels": (23, 50)}, [
            (1, "42.00 % (warn/crit at 23.00 %/50.00 %)", [
                ('filehandler_perc', 42.0, 23.0, 50.0, None, None),
            ]),
        ]),
    ],
}
