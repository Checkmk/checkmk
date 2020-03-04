# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore
checkname = 'snmp_uptime'

freeze_time = '1970-02-12 22:59:33'

info = [['124:21:26:42.03', '124:21:29:01.14']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (
                    0,
                    'Up since Sat Oct 11 02:30:32 1969, uptime: 124 days, 21:29:01',
                    [('uptime', 10790941, None, None, None, None)]
                )
            ]
        )
    ]
}
