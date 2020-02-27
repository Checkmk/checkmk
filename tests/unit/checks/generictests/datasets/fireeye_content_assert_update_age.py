# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore



checkname = 'fireeye_content'


info = [['456.180', '0', '2016/02/26 15:42:06']]

freeze_time = '2017-07-16T08:21:00'

discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'update_time_levels': (9000000, 10000000)},
                [(1, 'Update: failed', []),
                 (0, 'Last update: 2016/02/26 15:42:06', []),
                 (2, 'Age: 506 d (warn/crit at 104 d/116 d)', []),
                 (0, 'Security version: 456.180', [])])]}
