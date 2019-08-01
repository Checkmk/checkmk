# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_system'


info = [
    [u'System Status', u'Normal with Warning'],
    [u'System Model Number', u'Liebert HPC'],
    [u'Unit Operating State', u'standby'],
    [u'Unit Operating State Reason', u'Reason Unknown'],
]


discovery = {
    '': [
        (u'Liebert HPC', {}),
    ],
}


checks = {
    '': [
        (u'Liebert HPC', {}, [
            (0, u'System Model Number: Liebert HPC', []),
            (2, u'System Status: Normal with Warning', []),
            (0, u'Unit Operating State: standby', []),
            (0, u'Unit Operating State Reason: Reason Unknown', []),
        ]),
    ],
}
