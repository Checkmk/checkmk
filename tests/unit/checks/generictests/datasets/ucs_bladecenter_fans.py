# yapf: disable

checkname = 'ucs_bladecenter_fans'


info = [['equipmentNetworkElementFanStats',
         'Dn sys/switch-A/fan-module-1-1/fan-1/stats',
         'SpeedAvg 8542'],
        ['equipmentFanModuleStats',
         'Dn sys/chassis-2/fan-module-1-1/stats',
         'AmbientTemp 29.000000'],
        ['equipmentFan',
         'Dn sys/chassis-1/fan-module-1-1/fan-1',
         'Model N20-FAN5',
         'OperState operable'],
        ['equipmentFanStats',
         'Dn sys/chassis-2/fan-module-1-1/fan-1/stats',
         'SpeedAvg 3652']]


discovery = {'': [('Chassis 2', None), ('Switch A', None)],
             'temp': [('Ambient Chassis 2 FAN', {})]}


checks = {'': [('Chassis 2', {}, [(3, 'Fan statistics not available', [])]),
               ('Switch A', {}, [(3, 'Fan statistics not available', [])])],
          'temp': [('Ambient Chassis 2 FAN',
                    {'levels': (40, 50)},
                    [(0,
                      u'1 Sensors; Highest: 29.0 \xb0C, Average: 29.0 \xb0C, Lowest: 29.0 \xb0C',
                      [('temp', 29.0, None, None, None, None)])])]}
