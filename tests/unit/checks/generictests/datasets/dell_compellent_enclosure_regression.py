# -*- encoding: utf-8
# yapf: disable

checkname = 'dell_compellent_enclosure'

info = [
    [u'1', u'1', u'', u'TYP', u'MODEL', u'TAG'],
    [u'2', u'999', u'', u'TYP', u'MODEL', u'TAG'],
    [u'3', u'1', u'ATTENTION', u'TYP', u'MODEL', u'TAG'],
    [u'4', u'999', u'ATTENTION', u'TYP', u'MODEL', u'TAG'],
    [u'10', u'2', u'KAPUTT', u'TYP', u'MODEL', u'TAG'],
]

discovery = {'': [(u'1', None), (u'2', None), (u'3', None), (u'4', None), (u'10', None)]}

checks = {
    '': [
        (u'1', {}, [
            (0, 'Status: UP', []),
            (0, u'Model: MODEL, Type: TYP, Service-Tag: TAG', []),
        ]),
        (u'2', {}, [(3, u'Status: unknown[999]', []),
                    (0, u'Model: MODEL, Type: TYP, Service-Tag: TAG', [])]),
        (u'3', {}, [
            (0, 'Status: UP', []),
            (0, u'Model: MODEL, Type: TYP, Service-Tag: TAG', []),
            (0, u'State Message: ATTENTION', []),
        ]),
        (u'4', {}, [
            (3, u'Status: unknown[999]', []),
            (0, u'Model: MODEL, Type: TYP, Service-Tag: TAG', []),
            (3, u'State Message: ATTENTION', []),
        ]),
        (u'10', {}, [
            (2, u'Status: DOWN', []),
            (0, u'Model: MODEL, Type: TYP, Service-Tag: TAG', []),
            (2, u'State Message: KAPUTT', []),
        ]),
    ]
}
