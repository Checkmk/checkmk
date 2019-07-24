# -*- encoding: utf-8
# yapf: disable


checkname = 'ibm_storage_ts'


info = [[['3100 Storage', 'IBM', 'v1.2.3']],
        ['3'],
        [['0', '3', '1234567890', '2', '0', '2', ''],
         ['1', '3', '1234567891', '2', '2', '2', 'Message 2']],
        [['0', '9876543210', '0', '0', '0', '0'],
         ['1', '9876543211', '3', '4', '5', '6']]]


discovery = {'': [(None, None)],
             'drive': [('0', None), ('1', None)],
             'library': [('0', None), ('1', None)],
             'status': [(None, None)]}


checks = {'': [(None, {}, [(0, 'IBM 3100 Storage, Version v1.2.3', [])])],
          'drive': [('0', {}, [(0, 'S/N: 9876543210', [])]),
                    ('1',
                     {},
                     [(0, 'S/N: 9876543211', []),
                      (2, '4 hard write errors', []),
                      (1, '3 recovered write errors', []),
                      (2, '6 hard read errors', []),
                      (1, '5 recovered read errors', [])])],
          'library': [('0', {}, [(1, 'Device 1234567890, Status: Ok, Drives: 2', [])]),
                      ('1',
                       {},
                       [(1,
                         'Device 1234567891, Status: Ok, Drives: 2, Fault: Message 2 (2)',
                         [])])],
          'status': [(None, {}, [(0, 'Device Status: Ok', [])])]}