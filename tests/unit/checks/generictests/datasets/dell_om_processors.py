# -*- encoding: utf-8
# yapf: disable


checkname = 'dell_om_processors'


info = [['1', '1', 'Some manufacturer', '1', '0'],
        ['2', '2', 'Some manufacturer', '2', '1'],
        ['3', '3', 'Some manufacturer', '3', '2'],
        ['4', '4', 'Some manufacturer', '4', '32'],
        ['5', '4', 'Some manufacturer', '5', '128'],
        ['6', '5', 'Some manufacturer', '6', '256'],
        ['7', '6', 'Some manufacturer', '7', '512'],
        ['8', '6', 'Some manufacturer', '8', '1024']]


discovery = {'': [('1', None),
                  ('2', None),
                  ('3', None),
                  ('6', None),
                  ('7', None),
                  ('8', None)]}


checks = {'': [('1',
                {},
                [(2,
                  'Cpu (Some manufacturer) State: Other, CPU Reading: Unknown',
                  [])]),
               ('2',
                {},
                [(2,
                  'Cpu (Some manufacturer) State: Unknown, CPU Reading: Internal Error',
                  [])]),
               ('3',
                {},
                [(0,
                  'Cpu (Some manufacturer) State: Enabled, CPU Reading: Thermal Trip',
                  [])]),
               ('6',
                {},
                [(2,
                  'Cpu (Some manufacturer) State: BIOS Disabled, CPU Reading: Disabled',
                  [])]),
               ('7',
                {},
                [(2,
                  'Cpu (Some manufacturer) State: Idle, CPU Reading: Terminator Present',
                  [])]),
               ('8',
                {},
                [(2,
                  'Cpu (Some manufacturer) State: Idle, CPU Reading: Throttled',
                  [])])]}