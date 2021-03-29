# -*- encoding: utf-8
# yapf: disable

checkname = 'dell_compellent_disks'

info = [[
    [u'1', u'1', u'01-01', u'1', u'', u'1'],
    [u'2', u'999', u'01-02', u'1', u'', u'1'],
    [u'3', u'1', u'01-03', u'999', u'', u'1'],
    [u'4', u'1', u'01-04', u'0', u'ATTENTION', u'1'],
    [u'5', u'1', u'01-05', u'999', u'ATTENTION', u'1'],
    [u'10', u'2', u'01-10', u'0', u'KAPUTT', u'1'],
], [
    [u'serial1'], [u'serial2'], [u'serial3'], [u'serial4'], [u'serial5'], [u'serial10']
]]

discovery = {
    '': [(u'01-01', None), (u'01-02', None), (u'01-03', None), (u'01-04', None), (u'01-05', None), (u'01-10', None)]
}

checks = {
    '': [
        (u'01-01', {}, [
            (0, 'Status: UP', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: [u'serial1']", []),
        ]),
        (u'01-02', {}, [
            (3, u'Status: unknown[999]', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: [u'serial2']", []),
        ]),
        (u'01-03', {}, [
            (0, 'Status: UP', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: [u'serial3']", []),
        ]),
        (u'01-04', {}, [
            (0, 'Status: UP', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: [u'serial4']", []),
            (2, u'Health: not healthy, Reason: ATTENTION', []),
        ]),
        (u'01-05', {}, [
            (0, 'Status: UP', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: [u'serial5']", []),
            (3, u'Health: unknown[999], Reason: ATTENTION', []),
        ]),
        (u'01-10', {}, [
            (2, 'Status: DOWN', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: [u'serial10']", []),
            (2, u'Health: not healthy, Reason: KAPUTT', []),
        ]),
    ]
}
