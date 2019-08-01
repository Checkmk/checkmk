# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_cooling_position'


info = [
    [u'Free Cooling Valve Open Position', u'42', u'%'],
    [u'This is ignored', u'42', u'%'],
]


discovery = {
    '': [
        (u'Free Cooling Valve Open Position', {}),
    ],
}


checks = {
    '': [
        (u'Free Cooling Valve Open Position', {"levels": (23, 50)}, [
            (1, "42.00 % (warn/crit at 23.00 %/50.00 %)", [
                ('filehandler_perc', 42.0, 23.0, 50.0, None, None),
            ]),
        ]),
    ],
}
