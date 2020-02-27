# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore



checkname = 'df'


info = [
    [r'C:\\', 'NTFS', '62553084', '16898384', '45654700', '28%', r'C:\\'],
    ['SQL_Database_[GROUPME]', 'NTFS', '10450940', '2932348', '7518592', '29%', r'D:\\'],
    ['Scratch_Volume_[GROUPME]', 'NTFS', '5208060', '791864', '4416196', '16%', r'E:\\'],
]


mock_host_conf = {
        '': [[("myGroup", "GROUPME")]],
}


mock_host_conf_merged = {
        '': {"include_volume_name": True},
}


discovery = {'': [(r'C:\\ C://', {}),  # TODO: make this even more beautiful
                  ('SQL_Database_[GROUPME] D://', {}),
                  ('Scratch_Volume_[GROUPME] E://', {}),
                  ('myGroup', {'patterns': ['GROUPME']})]}


checks = {'': [(r'C:\\ C://',
                {'inodes_levels': (10.0, 5.0),
                 'levels': (80.0, 90.0),
                 'levels_low': (50.0, 60.0),
                 'magic_normsize': 20,
                 'show_inodes': 'onlow',
                 'show_levels': 'onmagic',
                 'show_reserved': False,
                 'trend_perfdata': True,
                 'trend_range': 24},
                [(0,
                  '27.01% used (16.12 of 59.66 GB)',
                  [('C://', 16502.328125, 48869.596875, 54978.296484375, 0, 61086.99609375),
                   ('fs_size', 61086.99609375, None, None, None, None),
                   ])]),

               ('myGroup',
                {'inodes_levels': (10.0, 5.0),
                 'levels': (80.0, 90.0),
                 'levels_low': (50.0, 60.0),
                 'magic_normsize': 20,
                 'patterns': ['GROUPME'],
                 'show_inodes': 'onlow',
                 'show_levels': 'onmagic',
                 'show_reserved': False,
                 'trend_perfdata': True,
                 'trend_range': 24},
                [(3, 'No filesystem matching the patterns', [])])]}


mock_host_conf = {'': [[('myGroup', 'GROUPME')]]}
