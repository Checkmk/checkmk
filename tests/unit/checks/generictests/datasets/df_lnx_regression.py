

checkname = 'df'


info = [[u'/dev/sda4',
         u'ext4',
         u'143786696',
         u'101645524',
         u'34814148',
         u'75%',
         u'/'],
        [u'[df_inodes_start]'],
        [u'/dev/sda4', u'ext4', u'9142272', u'1654272', u'7488000', u'19%', u'/'],
        [u'[df_inodes_end]']]


discovery = {'': [(u'/', {})]}


checks = {
    '': [
         (u'/', 'default',
             [(0, '75.8% used (103.92 of 137.13 GB), trend: 0.00 B / 24 hours',
                 [(u'/', 106418.50390625, 112333.35625, 126375.02578125, 0, 140416.6953125),
                  ('fs_size', 140416.6953125, None, None, None, None),
                  ('growth', 0.0, None, None, None, None),
                  ('trend', 0, None, None, 0, 5850.695638020833),
                  ('inodes_used', 1654272, 8228044.8, 8685158.4, 0, 9142272),
                 ]
              ),
             ]
         ),
         (u'/dev/sda4 /', 'default',
             [(0, '75.8% used (103.92 of 137.13 GB), trend: 0.00 B / 24 hours',
                 [(u'/', 106418.50390625, 112333.35625, 126375.02578125, 0, 140416.6953125),
                  ('fs_size', 140416.6953125, None, None, None, None),
                  ('growth', 0.0, None, None, None, None),
                  ('trend', 0, None, None, 0, 5850.695638020833),
                  ('inodes_used', 1654272, 8228044.8, 8685158.4, 0, 9142272),
                 ]
              ),
             ]
         ),
         (u'/', {"show_reserved": True},
             [(0, '75.8% used (103.92 of 137.13 GB), therein reserved for root: 5.1% (7155.30 MB),' \
                  ' trend: 0.00 B / 24 hours',
                 [(u'/', 106418.50390625, 112333.35625, 126375.02578125, 0, 140416.6953125),
                  ('fs_size', 140416.6953125, None, None, None, None),
                  ('reserved', 7155.296875, None, None, None, None),
                  ('growth', 0.0, None, None, None, None),
                  ('trend', 0, None, None, 0, 5850.695638020833),
                  ('inodes_used', 1654272, 8228044.8, 8685158.4, 0, 9142272),
                 ]
              ),
             ]
         ),
         (u'/dev/sda4 /', {"show_reserved": True},
             [(0, '75.8% used (103.92 of 137.13 GB), therein reserved for root: 5.1% (7155.30 MB),' \
                  ' trend: 0.00 B / 24 hours',
                 [(u'/', 106418.50390625, 112333.35625, 126375.02578125, 0, 140416.6953125),
                  ('fs_size', 140416.6953125, None, None, None, None),
                  ('reserved', 7155.296875, None, None, None, None),
                  ('growth', 0.0, None, None, None, None),
                  ('trend', 0, None, None, 0, 5850.695638020833),
                  ('inodes_used', 1654272, 8228044.8, 8685158.4, 0, 9142272),
                 ]
              ),
             ]
         ),
         (u'/home', 'default', [(3, 'filesystem not found', [])]
         ),
        ]
}
