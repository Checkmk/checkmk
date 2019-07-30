# yapf: disable
checkname = 'fileinfo'

info = [['1536557964'], ['[[[header]]]'], ['name', 'status', 'size', 'time'], ['[[[content]]]'],
        ['regular.txt', 'ok', '4242', '1536421281'], ['missing_file.txt', 'missing'],
        ['not_readable.txt', 'ok', '2323', '1536421281'], ['stat_failes.txt', 'stat failed: Permission denied']]

discovery = {
    '': [('not_readable.txt', {}), ('regular.txt', {}), ('stat_failes.txt', {})],
    'groups': []
}

checks = {
    '': [('regular.txt', {}, [(0, 'Size: 4242 B', [('size', 4242, None, None, None, None)]),
                              (0, 'Age: 37 h', [('age', 136683, None, None, None, None)])]),
         ('missinf_file.txt', {}, [(3, 'File not found', [])]),
         ('not_readable.txt', {}, [(0, 'Size: 2323 B', [('size', 2323, None, None, None, None)]),
                                   (0, 'Age: 37 h', [('age', 136683, None, None, None, None)])]),
         ('stat_failes.txt', {}, [(1, 'File stat failed', [])])],
}
