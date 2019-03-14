# yapf: disable


checkname = 'oracle_logswitches'


info = [['pengt', '15'], ['hirni', '22']]


discovery = {'': [('hirni', {}), ('pengt', {})]}


checks = {'': [('hirni',
                {'levels': (50, 100), 'levels_lower': (20, 15)},
                [(0,
                  '22 log switches in the last 60 minutes (warn/crit below 15/20) (warn/crit at 50/100)',
                  [('logswitches', 22, 50, 100, 0, None)])]),
               ('pengt',
                {'levels': (50, 100), 'levels_lower': (-1, -1)},
                [(0,
                  '15 log switches in the last 60 minutes (warn/crit below -1/-1) (warn/crit at 50/100)',
                  [('logswitches', 15, 50, 100, 0, None)])])]}
