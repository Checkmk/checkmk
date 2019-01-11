checkname = 'cups_queues'

info = [[
    'printer', 'spr1', 'is', 'idle.', 'enabled', 'since', 'Thu', 'Mar', '11', '14:28:23', '2010'
],
        [
            'printer', 'lpr2', 'now', 'printing', 'lpr2-3.', 'enabled', 'since', 'Tue', 'Jun', '29',
            '09:22:04', '2010'
        ],
        [
            'Wiederherstellbar:', 'Der', 'Netzwerk-Host', 'lpr2', 'ist', 'beschaeftigt,',
            'erneuter', 'Versuch', 'in', '30', 'Sekunden'
        ], ['---'], ['lpr2-2', 'root', '1024', 'Tue', 'Jun', '29', '09:02:35', '2010'],
        ['lpr2-3', 'root', '1024', 'Tue', 'Jun', '29', '09:05:54', '2010']]

discovery = {'': [('lpr2', {}), ('spr1', {})]}

checks = {
    '': [('lpr2', {
        'disabled_since': 2,
        'is_idle': 0,
        'job_age': (360, 720),
        'job_count': (5, 10),
        'now_printing': 0
    }, [(
        0,
        'now printing lpr2-3. enabled since Tue Jun 29 09:22:04 2010 (Wiederherstellbar: Der Netzwerk-Host lpr2 ist beschaeftigt, erneuter Versuch in 30 Sekunden)',
        []), (0, 'Jobs: 2', [('jobs', 2, 5, 10, 0, None)]),
        (2, 'Oldest job is from Tue Jun 29 09:02:35 2010', [])]),
         ('spr1', {
             'disabled_since': 2,
             'is_idle': 0,
             'job_age': (360, 720),
             'job_count': (5, 10),
             'now_printing': 0
         }, [(0, 'is idle. enabled since Thu Mar 11 14:28:23 2010', [])])]
}
