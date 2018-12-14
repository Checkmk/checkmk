

checkname = 'hp_proliant_psu'


info = [['0', '1', '3', '2', '80', '460'], ['0', '2', '3', '2', '105', '460']]


discovery = {'': [('0/1', None), ('0/2', None), ('Total', None)]}


checks = {'': [('0/1',
                {'levels': (80, 90)},
                [(0, 'Chassis 0/Bay 1', []),
                 (0, 'State: "ok"', []),
                 (0,
                  'Usage: 80 Watts',
                  [('power_usage_percentage', 17, None, None, None, None),
                   ('power_usage', 80, None, None, None, None)])]),
               ('0/2',
                {'levels': (80, 90)},
                [(0, 'Chassis 0/Bay 2', []),
                 (0, 'State: "ok"', []),
                 (0,
                  'Usage: 105 Watts',
                  [('power_usage_percentage', 22, None, None, None, None),
                   ('power_usage', 105, None, None, None, None)])]),
               ('Total',
                {'levels': (80, 90)},
                [(0,
                  'Usage: 185 Watts',
                  [('power_usage_percentage', 20, None, None, None, None),
                   ('power_usage', 185, None, None, None, None)])])]}
