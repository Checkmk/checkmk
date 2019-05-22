# -*- encoding: utf-8
# yapf: disable


checkname = 'sansymphony_pool'


info = [['Disk_pool_1', '57', 'Running', 'ReadWrite', 'Dynamic']]


discovery = {'': [('Disk_pool_1', 'sansymphony_pool_default_values')]}


checks = {'': [('Disk_pool_1',
                (80, 90),
                [(0,
                  'Dynamic pool Disk_pool_1 is running, its cache is in ReadWrite mode',
                  []),
                 (0,
                  'Pool allocation: 57%',
                  [('pool_allocation', 57, 80, 90, None, None)])])]}