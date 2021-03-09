# -*- encoding: utf-8
# yapf: disable

checkname = 'cisco_secure'

info = [
    [
        [u'1', u'FastEthernet1', u'2'],
        [u'2', u'TenGigabitEthernet1/1/1', u'1'],
        [u'3', u'TenGigabitEthernet1/1/2', u'1'],
        [u'4', u'TenGigabitEthernet1/1/3', u'1'],
        [u'5', u'TenGigabitEthernet1/1/4', u'2'],
    ],
    [
        [u'1', u'1', u'1', u'0', u'\x00\x11\x22\x33\x44\x55'],  # full operational
        [u'2', u'1', u'2', u'5', u'\x11\x22\x33\x44\x55\x66'],
        [u'3', u'2', u'3', u'0', u'\x22\x33\x44\x55\x66\x77'],
        [u'4', u'2', u'', u'0', u'\x33\x44\x55\x66\x77\x88'],
        [u'5', u'3', u'2', u'0', u'\x44\x55\x66\x77\x88\x99'],
        [u'6', u'3', u'2', u'0', u'\x55\x66\x77\x88\x99\xAA'],  # '6' is not in info[0]
    ],
]

discovery = {'': [(None, None)]}

checks = {
    '': [(
        None,
        {},
        [
            (
                1,
                u'Port TenGigabitEthernet1/1/1: could not be enabled due to certain reasons (violation count: 5, last MAC: 11:22:33:44:55:66)',
                [],
            ),
            (
                2,
                u'Port TenGigabitEthernet1/1/2: shutdown due to security violation (violation count: 0, last MAC: 22:33:44:55:66:77)',
                [],
            ),
            (
                3,
                u'Port TenGigabitEthernet1/1/3: unknown (violation count: 0, last MAC: 33:44:55:66:77:88)',
                [],
            ),
            (
                3,
                u'Port TenGigabitEthernet1/1/4: could not be enabled due to certain reasons (violation count: 0, last MAC: 44:55:66:77:88:99) unknown enabled state',
                [],
            ),
            (
                3,
                u'Port 6: could not be enabled due to certain reasons (violation count: 0, last MAC: 55:66:77:88:99:aa) unknown enabled state',
                [],
            ),
        ],
    )]
}
