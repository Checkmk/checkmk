# -*- encoding: utf-8
# yapf: disable

checkname = 'alcatel_timetra_cpu'

info = [['92']]

discovery = {'': [(None, 'alcatel_timetra_cpu_default_levels')]}

checks = {
    '': [(None, (90.0, 95.0), [(1, 'Total CPU: 92.0% (warn/crit at 90.0%/95.0%)',
                                [('util', 92, 90.0, 95.0, 0, 100)])])]
}
