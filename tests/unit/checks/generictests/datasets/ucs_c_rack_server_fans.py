# yapf: disable

checkname = 'ucs_c_rack_server_fans'


info = [['equipmentFan',
         'dn sys/rack-unit-1/fan-module-1-1/fan-1',
         'id 1',
         'model ',
         'operability operable'],
        ['equipmentFan',
         'dn sys/rack-unit-1/fan-module-1-1/fan-2',
         'id 2',
         'model ',
         'operability operable'],
        ['equipmentFan',
         'dn sys/rack-unit-2/fan-module-1-1/fan-1',
         'id 1',
         'model ',
         'operability operable'],
        ['equipmentFan',
         'dn sys/rack-unit-2/fan-module-1-1/fan-2',
         'id 2',
         'model ',
         'operability bla'],
        ['equipmentFan',
         'dn sys/rack-unit-2/fan-module-1-1/fan-3',
         'id 3',
         'model ',
         'operability blub']]


discovery = {'': [('Rack Unit 1 Module 1-1 1', {}),
                  ('Rack Unit 1 Module 1-1 2', {}),
                  ('Rack Unit 2 Module 1-1 1', {}),
                  ('Rack Unit 2 Module 1-1 2', {}),
                  ('Rack Unit 2 Module 1-1 3', {})]}


checks = {'': [('Rack Unit 1 Module 1-1 1',
                {},
                [(0, 'Operability Status is operable', [])]),
               ('Rack Unit 1 Module 1-1 2',
                {},
                [(0, 'Operability Status is operable', [])]),
               ('Rack Unit 2 Module 1-1 1',
                {},
                [(0, 'Operability Status is operable', [])]),
               ('Rack Unit 2 Module 1-1 2',
                {},
                [(3, 'Unknown Operability Status: bla', [])]),
               ('Rack Unit 2 Module 1-1 3',
                {},
                [(3, 'Unknown Operability Status: blub', [])])]}
