# -*- encoding: utf-8
# yapf: disable
checkname = 'innovaphone_priports_l1'

info = [['Foo', '1', '0', '23'], ['Bar', '2', '42', '23']]

discovery = {'': [('Bar', {'err_slip_count': 23})]}

freeze_time = "1970-01-01 00:00:00"

mock_item_state = {'': (-3, 0)}

checks = {
    '': [
        ('Bar', {'err_slip_count': 23}, [
            (0, 'Current state is UP', []),
            (2, 'Signal loss is 14.00/sec', []),
        ]),
        ('Foo', {'err_slip_count': 22}, [
            (2, 'Current state is Down', []),
            (2, 'Slip error count at 23', []),
        ]),
    ]
}
