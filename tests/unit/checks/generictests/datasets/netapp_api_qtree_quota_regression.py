# yapf: disable
checkname = 'netapp_api_qtree_quota'

info = [[
    'quota fd-content-db', 'quota-type tree', 'disk-limit 52428800', 'volume vol_bronze1_cifs',
    'disk-used 24430212'
],
        [
            'quota fd-interface-BPROD', 'quota-type tree', 'disk-limit 15728640',
            'volume vol_bronze1_cifs', 'disk-used 5241944'
        ],
        [
            'quota fd-interface-LEGACY', 'quota-type tree', 'disk-limit 10485760',
            'volume vol_bronze1_cifs', 'disk-used 4720520'
        ],
        [
            'quota fd-interface-BTEST', 'quota-type tree', 'disk-limit 10485760',
            'volume vol_bronze1_cifs', 'disk-used 4752'
        ],
        [
            'quota fd-interface-TCLONE', 'quota-type tree', 'disk-limit 10485760',
            'volume vol_bronze1_cifs', 'disk-used 6487460'
        ],
        [
            'quota fd-interface-BCLONE', 'quota-type tree', 'disk-limit 5242880',
            'volume vol_bronze1_cifs', 'disk-used 43884'
        ],
        [
            'quota fd-interface-BOFA', 'quota-type tree', 'disk-limit 5242880',
            'volume vol_bronze1_cifs', 'disk-used 963468'
        ],
        [
            'quota fd-interface-BRM', 'quota-type tree', 'disk-limit 1048576',
            'volume vol_bronze1_cifs', 'disk-used 96'
        ],
        [
            'quota jiraarchiv', 'quota-type tree', 'disk-limit 52428800', 'volume vol_bronze1_cifs',
            'disk-used 583932'
        ],
        [
            'quota CP-SOC_Malware', 'quota-type tree', 'disk-limit 10485760',
            'volume vol_bronze1_cifs', 'disk-used 148096'
        ],
        [
            'quota CP-SOC_Dokumente', 'quota-type tree', 'disk-limit 10485760',
            'volume vol_bronze1_cifs', 'disk-used 2013628'
        ],
        [
            'quota FD-MIS-Drop$', 'quota-type tree', 'disk-limit 31457280',
            'volume vol_bronze1_cifs', 'disk-used 1580324'
        ]]

discovery = {
    '': [('CP-SOC_Dokumente', {}), ('CP-SOC_Malware', {}), ('FD-MIS-Drop$', {}),
         ('fd-content-db', {}), ('fd-interface-BCLONE', {}), ('fd-interface-BOFA', {}),
         ('fd-interface-BPROD', {}), ('fd-interface-BRM', {}), ('fd-interface-BTEST', {}),
         ('fd-interface-LEGACY', {}), ('fd-interface-TCLONE', {}), ('jiraarchiv', {})]
}

checks = {
    '': [('CP-SOC_Dokumente', {
        'trend_range': 24,
        'show_levels': 'onmagic',
        'inodes_levels': (10.0, 5.0),
        'magic_normsize': 20,
        'show_inodes': 'onlow',
        'levels': (80.0, 90.0),
        'show_reserved': False,
        'levels_low': (50.0, 60.0),
        'trend_perfdata': True
    }, [(0, '19.2% used (1.92 of 10.00 GB), trend: 0.00 B / 24 hours',
         [('CP-SOC_Dokumente', 1966.43359375, 8192.0, 9216.0, 0, 10240.0),
          ('fs_size', 10240.0, None, None, None, None), ('growth', 0.0, None, None, None, None),
          ('trend', 0, None, None, 0, 426.6666666666667)])]),
         ('CP-SOC_Malware', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '1.41% used (144.62 MB of 10.00 GB), trend: 0.00 B / 24 hours',
              [('CP-SOC_Malware', 144.625, 8192.0, 9216.0, 0, 10240.0),
               ('fs_size', 10240.0, None, None, None, None), ('growth', 0.0, None, None, None,
                                                              None),
               ('trend', 0, None, None, 0, 426.6666666666667)])]),
         ('FD-MIS-Drop$', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '5.02% used (1.51 of 30.00 GB), trend: 0.00 B / 24 hours',
              [('FD-MIS-Drop$', 1543.28515625, 24576.0, 27648.0, 0, 30720.0),
               ('fs_size', 30720.0, None, None, None, None), ('growth', 0.0, None, None, None,
                                                              None),
               ('trend', 0, None, None, 0, 1280.0)])]),
         ('fd-content-db', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '46.6% used (23.30 of 50.00 GB), trend: 0.00 B / 24 hours',
              [('fd-content-db', 23857.62890625, 40960.0, 46080.0, 0, 51200.0),
               ('fs_size', 51200.0, None, None, None, None), ('growth', 0.0, None, None, None,
                                                              None),
               ('trend', 0, None, None, 0, 2133.3333333333335)])]),
         ('fd-interface-BCLONE', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '0.84% used (42.86 MB of 5.00 GB), trend: 0.00 B / 24 hours',
              [('fd-interface-BCLONE', 42.85546875, 4096.0, 4608.0, 0, 5120.0),
               ('fs_size', 5120.0, None, None, None, None), ('growth', 0.0, None, None, None, None),
               ('trend', 0, None, None, 0, 213.33333333333334)])]),
         ('fd-interface-BOFA', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '18.38% used (940.89 MB of 5.00 GB), trend: 0.00 B / 24 hours',
              [('fd-interface-BOFA', 940.88671875, 4096.0, 4608.0, 0, 5120.0),
               ('fs_size', 5120.0, None, None, None, None), ('growth', 0.0, None, None, None, None),
               ('trend', 0, None, None, 0, 213.33333333333334)])]),
         ('fd-interface-BPROD', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '33.33% used (5.00 of 15.00 GB), trend: 0.00 B / 24 hours',
              [('fd-interface-BPROD', 5119.0859375, 12288.0, 13824.0, 0, 15360.0),
               ('fs_size', 15360.0, None, None, None, None), ('growth', 0.0, None, None, None,
                                                              None),
               ('trend', 0, None, None, 0, 640.0)])]),
         ('fd-interface-BRM', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '0.009% used (96.00 kB of 1.00 GB), trend: 0.00 B / 24 hours',
              [('fd-interface-BRM', 0.09375, 819.2, 921.6, 0, 1024.0),
               ('fs_size', 1024.0, None, None, None, None), ('growth', 0.0, None, None, None, None),
               ('trend', 0, None, None, 0, 42.666666666666664)])]),
         ('fd-interface-BTEST', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '0.05% used (4.64 MB of 10.00 GB), trend: 0.00 B / 24 hours',
              [('fd-interface-BTEST', 4.640625, 8192.0, 9216.0, 0, 10240.0),
               ('fs_size', 10240.0, None, None, None, None), ('growth', 0.0, None, None, None,
                                                              None),
               ('trend', 0, None, None, 0, 426.6666666666667)])]),
         ('fd-interface-LEGACY', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '45.02% used (4.50 of 10.00 GB), trend: 0.00 B / 24 hours',
              [('fd-interface-LEGACY', 4609.8828125, 8192.0, 9216.0, 0, 10240.0),
               ('fs_size', 10240.0, None, None, None, None), ('growth', 0.0, None, None, None,
                                                              None),
               ('trend', 0, None, None, 0, 426.6666666666667)])]),
         ('fd-interface-TCLONE', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '61.87% used (6.19 of 10.00 GB), trend: 0.00 B / 24 hours',
              [('fd-interface-TCLONE', 6335.41015625, 8192.0, 9216.0, 0, 10240.0),
               ('fs_size', 10240.0, None, None, None, None), ('growth', 0.0, None, None, None,
                                                              None),
               ('trend', 0, None, None, 0, 426.6666666666667)])]),
         ('jiraarchiv', {
             'trend_range': 24,
             'show_levels': 'onmagic',
             'inodes_levels': (10.0, 5.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'levels': (80.0, 90.0),
             'show_reserved': False,
             'levels_low': (50.0, 60.0),
             'trend_perfdata': True
         }, [(0, '1.11% used (570.25 MB of 50.00 GB), trend: 0.00 B / 24 hours',
              [('jiraarchiv', 570.24609375, 40960.0, 46080.0, 0, 51200.0),
               ('fs_size', 51200.0, None, None, None, None), ('growth', 0.0, None, None, None,
                                                              None),
               ('trend', 0, None, None, 0, 2133.3333333333335)])])]
}
