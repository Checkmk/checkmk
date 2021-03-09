# yapf: disable


checkname = 'mongodb_mem'


info = [[u'resident', u'79'],
        [u'supported', u'True'],
        [u'virtual', u'1021'],
        [u'mappedWithJournal', u'0'],
        [u'mapped', u'0'],
        [u'bits', u'64'],
        [u'note', u'fields', u'vary', u'by', u'platform'],
        [u'page_faults', u'9']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0,
                  'Resident usage: 79 MB',
                  [('process_resident_size', 82837504, None, None, None, None)]),
                 (0,
                  'Virtual usage: 1021 MB',
                  [('process_virtual_size', 1070596096, None, None, None, None)]),
                 (0,
                  'Mapped usage: 0 B',
                  [('process_mapped_size', 0, None, None, None, None)])])]}
