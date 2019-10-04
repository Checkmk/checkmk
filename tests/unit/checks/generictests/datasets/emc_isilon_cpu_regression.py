# -*- encoding: utf-8
# yapf: disable

checkname = 'emc_isilon_cpu'

info = [['123', '234', '231', '567']]

discovery = {'': [(None, {})]}

checks = {
    '': [(None, {}, [
        (0, 'User: 35.7%', [('user', 35.7, None, None, None, None)]),
        (0, 'System: 23.1%', [('system', 23.1, None, None, None, None)]),
        (0, 'Interrupt: 56.7%', [('interrupt', 56.7, None, None, None, None)]),
        (0, 'Total: 115%', [])
    ]),
       (None, None, [
        (0, 'User: 35.7%', [('user', 35.7, None, None, None, None)]),
        (0, 'System: 23.1%', [('system', 23.1, None, None, None, None)]),
        (0, 'Interrupt: 56.7%', [('interrupt', 56.7, None, None, None, None)]),
        (0, 'Total: 115%', [])
    ])]
}
