# yapf: disable


checkname = 'mongodb_mem'

info = [['resident', '856'],
        ['supported', 'True'],
        ['virtual', '6100'],
        ['mappedWithJournal', '5374'],
        ['bits', '64'],
        ['note', 'fields', 'vary', 'by', 'platform'],
        ['page_faults', '86'],
        ['heap_usage_bytes', '65501032']]

discovery = {'': [(None, {})]}

checks = {'': [(None,
                {},
                [(0,
                  'Resident usage: 856.00 MB',
                  [('process_resident_size', 897581056, None, None, None, None)]),
                 (0,
                  'Virtual usage: 5.96 GB',
                  [('process_virtual_size', 6396313600, None, None, None, None)])
                 ])]}