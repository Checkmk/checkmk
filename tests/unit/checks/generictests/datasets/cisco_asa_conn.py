# -*- encoding: utf-8
# yapf: disable


checkname = 'cisco_asa_conn'


info = [[['0', 'interface 0'], ['1', 'interface 1']],
        [['0', '123.456.789.0'], ['1', '123.456.789.1']],
        [['0', '1', '1'], ['1', '9', '7']]]


discovery = {'': [('0', None)]}


checks = {'': [('0',
                {},
                [(0, 'Name: interface 0', []),
                 (0, 'IP: 123.456.789.0', []),
                 (0, 'Status: up', [])])]}
