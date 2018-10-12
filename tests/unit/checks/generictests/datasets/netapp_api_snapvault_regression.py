

checkname = 'netapp_api_snapvault'


info = [['snapvault /vol/ipb_datap/',
         'status idle state snapvaulted',
         'lag-time 53812',
         'source-system 172.31.12.15'],
        ['snapvault /vol/ipb_datas/',
         'status idle state snapvaulted',
         'lag-time 53812',
         'source-system 172.31.12.15'],
        ['snapvault /vol/ipb_user/',
         'status idle state snapvaulted',
         'lag-time 97007',
         'source-system 172.31.12.15'],
        ['snapvault /vol/ipb_vol0/',
         'status idle state snapvaulted',
         'lag-time 97011',
         'source-system 172.31.12.15']]


discovery = {'': [('/vol/ipb_datap/', {}),
                  ('/vol/ipb_datas/', {}),
                  ('/vol/ipb_user/', {}),
                  ('/vol/ipb_vol0/', {})]}


checks = {'': [('/vol/ipb_datap/',
                'default',
                [(0, 'Source-System: 172.31.12.15', []),
                 (0, 'Status: idle state snapvaulted', []),
                 (0, 'Lag-Time: 14 h', [])]),
               ('/vol/ipb_datas/',
                'default',
                [(0, 'Source-System: 172.31.12.15', []),
                 (0, 'Status: idle state snapvaulted', []),
                 (0, 'Lag-Time: 14 h', [])]),
               ('/vol/ipb_user/',
                'default',
                [(0, 'Source-System: 172.31.12.15', []),
                 (0, 'Status: idle state snapvaulted', []),
                 (0, 'Lag-Time: 26 h', [])]),
               ('/vol/ipb_vol0/',
                'default',
                [(0, 'Source-System: 172.31.12.15', []),
                 (0, 'Status: idle state snapvaulted', []),
                 (0, 'Lag-Time: 26 h', [])])]}
