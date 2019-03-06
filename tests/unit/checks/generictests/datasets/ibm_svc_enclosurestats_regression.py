# yapf: disable


checkname = 'ibm_svc_enclosurestats'


info = [[u'1', u'power_w', u'207', u'218', u'140410113051'],
        [u'1', u'temp_c', u'22', u'22', u'140410113246'],
        [u'1', u'temp_f', u'71', u'71', u'140410113246'],
        [u'2', u'power_w', u'126', u'128', u'140410113056'],
        [u'2', u'temp_c', u'21', u'21', u'140410113246'],
        [u'2', u'temp_f', u'69', u'69', u'140410113246'],
        [u'3', u'power_w', u'123', u'126', u'140410113041'],
        [u'3', u'temp_c', u'22', u'22', u'140410113246'],
        [u'3', u'temp_f', u'71', u'71', u'140410113246'],
        [u'4', u'power_w', u'133', u'138', u'140410112821'],
        [u'4', u'temp_c', u'22', u'23', u'140410112836'],
        [u'4', u'temp_f', u'71', u'73', u'140410112836']]


discovery = {'power': [(u'1', {}), (u'2', {}), (u'3', {}), (u'4', {})],
             'temp': [(u'1', {}), (u'2', {}), (u'3', {}), (u'4', {})]}


checks = {'power': [(u'1',
                     {},
                     [(0,
                       u'207 Watt',
                       [('power', 207, None, None, None, None)])]),
                    (u'2',
                     {},
                     [(0,
                       u'126 Watt',
                       [('power', 126, None, None, None, None)])]),
                    (u'3',
                     {},
                     [(0,
                       u'123 Watt',
                       [('power', 123, None, None, None, None)])]),
                    (u'4',
                     {},
                     [(0,
                       u'133 Watt',
                       [('power', 133, None, None, None, None)])])],
          'temp': [(u'1',
                    {'levels': (35, 40)},
                    [(0, u'22 \xb0C', [('temp', 22, 35, 40, None, None)])]),
                   (u'2',
                    {'levels': (35, 40)},
                    [(0, u'21 \xb0C', [('temp', 21, 35, 40, None, None)])]),
                   (u'3',
                    {'levels': (35, 40)},
                    [(0, u'22 \xb0C', [('temp', 22, 35, 40, None, None)])]),
                   (u'4',
                    {'levels': (35, 40)},
                    [(0, u'22 \xb0C', [('temp', 22, 35, 40, None, None)])])]}
