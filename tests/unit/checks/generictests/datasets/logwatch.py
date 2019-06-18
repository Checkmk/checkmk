# -*- encoding: utf-8
# yapf: disable


checkname = 'logwatch'


info = [[None, '[[[mylog]]]'],
        [None, 'C', 'whoha!', 'Someone', 'mooped!'],
        [None, '[[[missinglog:missing]]]'],
        [None, '[[[unreadablelog:cannotopen]]]'],
        [None, '[[[empty.log]]]'],
        [None, '[[[my_other_log]]]'],
        [None, 'W', 'watch', 'your', 'step!']]


discovery = {
    '': [
        ('empty.log', None),
        ('my_other_log', None),
        ('mylog', None)],
    'ec': [],
    'ec_single': [],
    'groups': []}


checks = {
    '': [
        ('empty.log', {}, [
            (0, 'no error messages', []),
        ]),
        ('my_other_log', {}, [
            (1, '2 WARN messages (Last worst: "watch your step!")', []),
        ]),
        ('mylog', {}, [
            (2, '2 CRIT messages (Last worst: "whoha! Someone mooped!")', []),
        ]),
    ],
}
