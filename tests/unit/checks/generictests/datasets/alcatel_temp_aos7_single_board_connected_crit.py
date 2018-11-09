

checkname = 'alcatel_temp_aos7'


info = [['50',
         '0',
         '0',
         '0',
         '0',
         '0',
         '0',
         '0',
         '0',
         '0',
         '0',
         '0',
         '0',
         '0',
         '0',
         '0']]


discovery = {'': [('CPMA', {})]}


checks = {'': [('CPMA',
                {'levels': (45, 50)},
                [(2,
                  u'50 \xb0C (warn/crit at 45/50 \xb0C)',
                  [('temp', 50, 45, 50, None, None)])])]}
