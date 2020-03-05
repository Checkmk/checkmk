# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore
checkname = 'rabbitmq_vhosts'

info = [
    [
        '{"description": "Default virtual host", "message_stats": {"publish": 2, "publish_details": {"rate": 0.0}}, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "/"}'
    ]
]

discovery = {'': [('/', {})]}

checks = {
    '': [
        (
            '/', {}, [
                (0, 'Description: Default virtual host', []),
                (
                    0, 'Total number of messages: 0', [
                        ('messages', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Ready messages: 0', [
                        ('messages_ready', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Unacknowledged messages: 0', [
                        ('messages_unacknowledged', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Published messages: 2', [
                        ('message_publish', 2, None, None, None, None)
                    ]
                ),
                (
                    0, 'Rate: 0.0 1/s', [
                        ('message_publish_rate', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
