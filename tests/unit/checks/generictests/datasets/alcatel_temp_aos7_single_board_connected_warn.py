checkname = 'alcatel_temp_aos7'

info = [['45', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0']]

discovery = {'': [('CPMA', {})]}

checks = {
    '': [('CPMA', {
        'levels': (45, 50)
    }, [(1, u'45 \xb0C (warn/crit at 45/50 \xb0C)', [('temp', 45, 45, 50, None, None)])])]
}
