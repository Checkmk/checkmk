# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_system_events'


info = [
    [u'Ambient Air Temperature Sensor Issue', u'Inactive Event'],
    [u'Supply Fluid Over Temp', u'Inactive Event'],
    [u'Supply Fluid Under Temp', u'Inactive Event'],
    [u'Supply Fluid Temp Sensor Issue', u'Active Warning'],
]


discovery = {
    '': [
        (None, {}),
    ],
}


checks = {
    '': [
        (None, {}, [
            (2, u'Supply Fluid Temp Sensor Issue: Active Warning', []),
        ]),
    ],
}
