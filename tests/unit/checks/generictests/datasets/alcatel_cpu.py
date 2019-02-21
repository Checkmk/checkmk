# yapf: disable
checkname = 'alcatel_cpu'

info = [['17', 'doesnt matter', 'doesnt matter'], ['doesnt matter']]

discovery = {'': [(None, 'alcatel_cpu_default_levels')]}

checks = {'': [(None, (90.0, 95.0), [(0, 'total: 17.0%', [('util', 17, 90.0, 95.0, 0, 100)])])]}
