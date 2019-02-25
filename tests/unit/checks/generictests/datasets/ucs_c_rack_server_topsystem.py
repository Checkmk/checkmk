# yapf: disable

checkname = 'ucs_c_rack_server_topsystem'


info = [['topSystem',
         'dn sys',
         'address 192.168.1.1',
         'currentTime Wed Feb  6 09:12:12 2019',
         'mode stand-alone',
         'name CIMC-istreamer2a-etn']]


discovery = {'': [(None, None)]}


checks = {'': [(None,
                {},
                [(0, 'DN: sys', []),
                 (0, 'IP: 192.168.1.1', []),
                 (0, 'Mode: stand-alone', []),
                 (0, 'Name: CIMC-istreamer2a-etn', []),
                 (0, 'Date and time: 2019-02-06 09:12:12', [])])]}
