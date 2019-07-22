# yapf: disable
checkname = 'netapp_api_luns'

info = [[
    'lun /vol/iscsi_crm_dblogs/crm_dblogs_lu01', 'read-only false', 'size 644286182400',
    'vserver ISCSI_CRM', 'size-used 538924421120', 'online true', 'volume iscsi_crm_dblogs'
],
        [
            'lun /vol/iscsi_crm_dbprod/crm_dbprod_lu01', 'read-only false', 'size 2638883681280',
            'vserver ISCSI_CRM', 'size-used 2362467872768', 'online true', 'volume iscsi_crm_dbprod'
        ],
        [
            'lun /vol/iscsi_crm_dbtemp/crm_dbtemp_lu01', 'read-only false', 'size 697997260800',
            'vserver ISCSI_CRM', 'size-used 582014812160', 'online true', 'volume iscsi_crm_dbtemp'
        ],
        [
            'lun /vol/iscsi_nice_db/nice_db_lun', 'read-only false', 'size 644286182400',
            'vserver ISCSI_NICE_NOVO', 'size-used 435543142400', 'online true',
            'volume iscsi_nice_db'
        ]]

discovery = {
    '': [('crm_dblogs_lu01', {}), ('crm_dbprod_lu01', {}), ('crm_dbtemp_lu01', {}),
         ('nice_db_lun', {})]
}

checks = {
    '': [('crm_dblogs_lu01', {
        'read_only': False,
        'trend_range': 24,
        'levels': (80.0, 90.0),
        'trend_perfdata': True
    }, [(1, '83.65% used (501.91 of 600.04 GB), trend: 0.00 B / 24 hours',
         [('crm_dblogs_lu01', 513958.37890625, 491551.34765625, 552995.2661132812, 0,
           614439.1845703125), ('fs_size', 614439.1845703125, None, None, None, None),
          ('growth', 0.0, None, None, None, None), ('trend', 0, None, None, 0,
                                                    25601.632690429688)])]),
         ('crm_dbprod_lu01', {
             'read_only': False,
             'trend_range': 24,
             'levels': (80.0, 90.0),
             'trend_perfdata': True
         }, [(1, '89.53% used (2.15 of 2.40 TB), trend: 0.00 B / 24 hours',
              [('crm_dbprod_lu01', 2253024.93359375, 2013308.47265625, 2264972.0317382812, 0,
                2516635.5908203125), ('fs_size', 2516635.5908203125, None, None, None, None),
               ('growth', 0.0, None, None, None, None),
               ('trend', 0, None, None, 0, 104859.81628417969)])]),
         ('crm_dbtemp_lu01', {
             'read_only': False,
             'trend_range': 24,
             'levels': (80.0, 90.0),
             'trend_perfdata': True
         }, [(1, '83.38% used (542.04 of 650.06 GB), trend: 0.00 B / 24 hours',
              [('crm_dbtemp_lu01', 555052.578125, 532529.6484375, 599095.8544921875, 0,
                665662.060546875), ('fs_size', 665662.060546875, None, None, None, None),
               ('growth', 0.0, None, None, None, None),
               ('trend', 0, None, None, 0, 27735.919189453125)])]),
         ('nice_db_lun', {
             'read_only': False,
             'trend_range': 24,
             'levels': (80.0, 90.0),
             'trend_perfdata': True
         }, [(0, '67.6% used (405.63 of 600.04 GB), trend: 0.00 B / 24 hours',
              [('nice_db_lun', 415366.30859375, 491551.34765625, 552995.2661132812, 0,
                614439.1845703125), ('fs_size', 614439.1845703125, None, None, None, None),
               ('growth', 0.0, None, None, None, None),
               ('trend', 0, None, None, 0, 25601.632690429688)])])]
}
