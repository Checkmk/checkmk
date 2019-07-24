# yapf: disable


checkname = 'esx_vsphere_datastores'


info = [
    [u'[WIN-0108-MCC35-U-L008-SSD-EXC2]'],
    [u'accessible', u'true'],
    [u'capacity', u'13193871097856'],
    [u'freeSpace', u'2879343558656'],
    [u'type', u'VMFS'],
    [u'uncommitted', u'0'],
    [u'url', u'/vmfs/volumes/5bacc6e6-1f214d64-5023-901b0e6d02d5'],
    [u'[WIN-0100-MCC15-M-L000-SSD]'],
    [u'accessible', u'true'],
    [u'capacity', u'4397778075648'],
    [u'freeSpace', u'3310200291328'],
    [u'type', u'VMFS'],
    [u'uncommitted', u'0'],
    [u'url', u'/vmfs/volumes/5bc5b243-c6c57438-bc07-4c52621258cd']]


discovery = {'': [(u'WIN-0100-MCC15-M-L000-SSD', {}),
                  (u'WIN-0108-MCC35-U-L008-SSD-EXC2', {})]}


checks = {'': [(u'WIN-0100-MCC15-M-L000-SSD',
                {'inodes_levels': (10.0, 5.0),
                 'levels': (80.0, 90.0),
                 'levels_low': (50.0, 60.0),
                 'magic_normsize': 20,
                 'show_inodes': 'onlow',
                 'show_levels': 'onmagic',
                 'show_reserved': False,
                 'trend_perfdata': True,
                 'trend_range': 24},
                [(0, '24.73% used (1012.89 GB of 4.00 TB), trend: 0.00 B / 24 hours', [
                    ('WIN-0100-MCC15-M-L000-SSD', 1037195.0, 3355238.4, 3774643.2, 0, 4194048.0),
                    ('fs_size', 4194048.0, None, None, None, None),
                    ('growth', 0.0, None, None, None, None),
                    ('trend', 0, None, None, 0, 174752.0),
                   ]),
                 (0, 'Uncommitted: 0.00 B', [('uncommitted', 0.0, None, None, None, None)]),
                 (0, 'Provisioning: 24.73%', []),
                 (0, "", [('overprovisioned', 1037195.0, None, None, None, None)]),
                ]),
               (u'WIN-0108-MCC35-U-L008-SSD-EXC2',
                {'provisioning_levels': (70.0, 80.0)},
                [(0, '78.18% used (9.38 of 12.00 TB), trend: 0.00 B / 24 hours', [
                    (u'WIN-0108-MCC35-U-L008-SSD-EXC2', 9836700.0, 10066124.8, 11324390.4, 0, 12582656.0),
                    ('fs_size', 12582656.0, None, None, None, None),
                    ('growth', 0.0, None, None, None, None),
                    ('trend', 0, None, None, 0, 524277.3333333333),
                   ]),
                 (0, 'Uncommitted: 0.00 B', [('uncommitted', 0.0, None, None, None, None)]),
                 (1, 'Provisioning: 78.18% (warn/crit at 70.0%/80.0%)', []),
                 (0, "", [('overprovisioned', 9836700.0, 8807859.2, 10066124.8, None, None)]),
                ]),
               (u'WIN-0108-MCC35-U-L008-SSD-EXC2',
                {'inodes_levels': (10.0, 5.0),
                 'levels': (80.0, 90.0),
                 'levels_low': (50.0, 60.0),
                 'magic_normsize': 20,
                 'show_inodes': 'onlow',
                 'show_levels': 'onmagic',
                 'show_reserved': False,
                 'trend_perfdata': True,
                 'trend_range': 24},
                [(0, '78.18% used (9.38 of 12.00 TB), trend: 0.00 B / 24 hours', [
                    (u'WIN-0108-MCC35-U-L008-SSD-EXC2', 9836700.0, 10066124.8, 11324390.4, 0, 12582656.0),
                    ('fs_size', 12582656.0, None, None, None, None),
                    ('growth', 0.0, None, None, None, None),
                    ('trend', 0, None, None, 0, 524277.3333333333),
                   ]),
                 (0, 'Uncommitted: 0.00 B', [('uncommitted', 0.0, None, None, None, None)]),
                 (0, 'Provisioning: 78.18%', []),
                 (0, "", [('overprovisioned', 9836700.0, None, None, None, None)]),
                ])],
}
