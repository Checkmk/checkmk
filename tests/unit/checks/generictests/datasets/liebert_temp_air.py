# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_temp_air'


info = [
    [u'Return Air Temperature', u'107.6', u'deg F', u'Some made-up Air Temperature', u'Unavailable', u'deg C']
]


extra_sections = {
    '': [
        {u'System Model Number': 'Liebert CRV',
         u'System Status': 'Normal Operation',
         u'Unit Operating State': 'standby',
         u'Unit Operating State Reason': 'Reason Unknown'},
    ],
}


discovery = {
    '': [
        (u'Return', {}),
    ],
}


checks = {
    '': [
        (u'Return', {'levels': (50, 55), 'levels_lower': (10, 15)}, [
            (0, u'42.0 \xb0C', [
                ('temp', 42.0, 50.0, 55.0, None, None),
            ]),
        ]),
        (u'Some made-up', {'levels': (50, 55), 'levels_lower': (10, 15)}, [
            (0, "Unit is in standby (unavailable)", []),
        ]),
    ],
}
