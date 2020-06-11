# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore
checkname = 'rabbitmq_queues'

info = [
    [
        '{"memory": 16780, "message_stats": {"publish": 5, "publish_details": {"rate": 0.0}}, "messages": 5, "messages_ready": 5, "messages_unacknowledged": 0, "name": "hello", "node": "rabbit@my-rabbit", "state": "running", "type": "classic"}'
    ],
    [
        '{"memory": 9816, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "my_queue2", "node": "rabbit@my-rabbit", "state": "running", "type": "classic"}'
    ],
    [
        '{"memory": 68036, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "my_queue3", "node": "rabbit@my-rabbit", "state": "running", "type": "quorum"}'
    ]
]

discovery = {'': [('hello', {}), ('my_queue2', {}), ('my_queue3', {})]}

checks = {
    '': [
        (
            'hello', {}, [
                (0, 'Type: Classic', []), (0, 'Is running: running', []),
                (0, 'Running on node: rabbit@my-rabbit', []),
                (
                    0, 'Total number of messages: 5', [
                        ('messages', 5, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages ready: 5', [
                        ('messages_ready', 5, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages unacknowledged: 0', [
                        ('messages_unacknowledged', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages published: 5', [
                        ('messages_publish', 5, None, None, None, None)
                    ]
                ),
                (
                    0, 'Rate: 0 1/s', [
                        ('messages_publish_rate', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Memory used: 16.39 kB', [
                        ('mem_lnx_total_used', 16780, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'my_queue2', {}, [
                (0, 'Type: Classic', []), (0, 'Is running: running', []),
                (0, 'Running on node: rabbit@my-rabbit', []),
                (
                    0, 'Total number of messages: 0', [
                        ('messages', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages ready: 0', [
                        ('messages_ready', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages unacknowledged: 0', [
                        ('messages_unacknowledged', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Memory used: 9.59 kB', [
                        ('mem_lnx_total_used', 9816, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'my_queue3', {}, [
                (0, 'Type: Quorum', []), (0, 'Is running: running', []),
                (0, 'Running on node: rabbit@my-rabbit', []),
                (
                    0, 'Total number of messages: 0', [
                        ('messages', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages ready: 0', [
                        ('messages_ready', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Messages unacknowledged: 0', [
                        ('messages_unacknowledged', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Memory used: 66.44 kB', [
                        ('mem_lnx_total_used', 68036, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
