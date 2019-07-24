# -*- encoding: utf-8
# yapf: disable


checkname = 'hyperv_vms'


info = [[u'"Name"', u'"State"', u'"Uptime"', u'"Status"'],
        [u'"AUN-CAA"', u'"Off"', u'"00:00:00"', u'"Operating normally"'],
        ['Q-WSUS', 'Running', '4.21:44:29', 'Operating normally'],
        ['weg-ca-webserver', 'Off', '00:00:00', 'Operating normally'],
        ['z4058044_snap (23.05.2014 - 09:29:29)',
         'Running',
         '18:20:34',
         'Operating normally'],
        ['& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot'],
        [''],
]


discovery = {'': [('Q-WSUS', {'state': 'Running'}),
                  ('weg-ca-webserver', {'state': 'Off'}),
                  ('z4058044_snap (23.05.2014 - 09:29:29)', {'state': 'Running'}),
                  (u'AUN-CAA', {'state': u'Off'})]}


checks = {'': [('Q-WSUS',
                {'state': 'Running'},
                [(0, 'State is Running (Operating normally)', [])]),
               ('weg-ca-webserver',
                {'state': 'Off'},
                [(0, 'State is Off (Operating normally)', [])]),
               ('z4058044_snap (23.05.2014 - 09:29:29)',
                {'state': 'Running'},
                [(0, 'State is Running (Operating normally)', [])]),
               (u'AUN-CAA',
                {'state': u'Off'},
                [(0, u'State is Off (Operating normally)', [])])]}
