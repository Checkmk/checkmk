# -*- encoding: utf-8
# yapf: disable


checkname = 'mcafee_webgateway'


info = [['', '20']]


freeze_time = '2019-05-27T05:30:07'


mock_item_state = {
    '': {
        'check_mcafee_webgateway.infections': (1558935006., 2),
        'check_mcafee_webgateway.connections_blocked': (1558935006., 2),
    },
}


discovery = {'': [(None, {})]}


checks = {
    '': [
        (None, {}, [
            (0, 'Connections blocked: 18.0/s', [
                ('connections_blocked_rate', 18.0, None, None, None, None),
            ]),
        ]),
        (None, {'infections': (5, 10), 'connections_blocked': (10, 15)}, [
            (2, 'Connections blocked: 18.0/s (warn/crit at 10.0/s/15.0/s)', [
                ('connections_blocked_rate', 18.0, 10, 15, None, None),
            ]),
        ]),
    ],
}
