# -*- encoding: utf-8
# yapf: disable


checkname = 'docker_container_cpu'


freeze_time = '1970-01-01-T00:00:10'


info = [['cpu',
         '68155010',
         '531',
         '39064746',
         '39150793201',
         '667787',
         '0',
         '1534011',
         '0',
         '40424050',
         '0'],
        ['num_cpus', '56'],
        ['user', '612160'],
        ['system', '342799']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0,
                  'Total CPU: 0.14%',
                  [('util', 0.1360733690431687, None, None, 0, 100)])])]}


mock_item_state = {'': (0, 0)}