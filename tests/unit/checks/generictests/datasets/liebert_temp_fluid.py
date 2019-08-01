# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_temp_fluid'


info = [
    [u'Supply Fluid Temp Set Point 1', u'18.0', u'deg C',
     u'Supply Fluid Temp Set Point 2', u'14', u'deg C',
     u'Supply Fluid Over Temp Alarm Threshold', u'22', u'deg C',
     u'Supply Fluid Under Temp Warning Threshold', u'0', u'deg C',
     u'Supply Fluid Under Temp Alarm Threshold', u'0', u'deg C',
     u'Supply Fluid Over Temp Warning Threshold', u'0', u'deg C'],
]



discovery = {
    '': [
        (u'Supply Fluid Temp Set Point 1', {}),
        (u'Supply Fluid Temp Set Point 2', {}),
    ],
}


checks = {
    '': [
        (u'Supply Fluid Temp Set Point 1', {}, [
            (0, u'18.0 \xb0C', [
                ('temp', 18.0, 22.0, 22.0, None, None),
            ]),
        ]),
    ],
}
