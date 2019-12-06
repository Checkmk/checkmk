# -*- encoding: utf-8
# yapf: disable
checkname = 'graylog_sources'

info = [
    [
        u'{"sources": {"my_source_1": 81216, "my_source_2": 10342}, "range": 0, "total": 1, "took_ms": 3}'
    ]
]

discovery = {'': [(u'my_source_1', {}), (u'my_source_2', {})]}

checks = {
    '': [
        (
            u'my_source_1', {}, [
                (
                    0, 'Total number of messages: 81216', [
                        ('messages', 81216, None, None, None, None)
                    ]
                ),
                (
                    0, 'Average number of messages (30 m): 0.00', [
                        ('msgs_avg', 0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'my_source_2', {}, [
                (
                    0, 'Total number of messages: 10342', [
                        ('messages', 10342, None, None, None, None)
                    ]
                ),
                (
                    0, 'Average number of messages (30 m): 0.00', [
                        ('msgs_avg', 0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
