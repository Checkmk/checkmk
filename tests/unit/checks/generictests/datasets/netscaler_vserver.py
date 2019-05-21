# -*- encoding: utf-8
# yapf: disable


checkname = 'netscaler_vserver'


info = [[None,
         'verser0',
         '123.456.78.9',
         '80',
         '0',
         '7',
         '1',
         '5',
         '200',
         '100',
         '300',
         'Full VServer Name']]


discovery = {'': [('Full VServer Name', {})]}


checks = {'': [('Full VServer Name',
                {'cluster_status': 'best', 'health_levels': (100.0, 0.1)},
                [(0, 'Status: up', []),
                 (0,
                  'Type: cache redirection, Protocol: http, Socket: 123.456.78.9:80',
                  []),
                 (0,
                  'Request rate: 200/s, In: 100.00 B/s, Out: 300.00 B/s',
                  [('request_rate', 200, None, None, None, None),
                   ('if_in_octets', 100, None, None, None, None),
                   ('if_out_octets', 300, None, None, None, None)])])]}