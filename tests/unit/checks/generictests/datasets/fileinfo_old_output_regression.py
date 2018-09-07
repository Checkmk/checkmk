

checkname = 'fileinfo'


info = [['1536557964'],
        ['regular.txt', '4242', '1536421281'],
        ['missing_file.txt', 'missing'],
        ['not_readable.txt', 'not readable', '1536421281'],
        ['stat_failes.txt', '', '', '0000'],
]


discovery = {'': [('not_readable.txt', {}), ('regular.txt', {}), ('stat_failes.txt', {})],
             'groups': []}


checks = {'': [('regular.txt', 'default',
                [(0, 'Size: 4242 B, Age: 37 h', [('size', 4242, None, None, None, None),
                                                 ('age', 136683, None, None, None, None)])]),
               ('missinf_file.txt', 'default',
                [(3, 'File not found', [])]),
               ('not_readable.txt', 'default', [(1, 'File stat failed', [])]),
               ('stat_failes.txt', 'default', [(1, 'File stat failed', [])]),
              ],
}
