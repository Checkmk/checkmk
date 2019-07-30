# -*- encoding: utf-8
# yapf: disable


checkname = 'teracom_tcw241_analog'


info = [[[u'1.0', u'Tank_Level', u'80000', u'10000'],
         [u'2.0', u'Motor_Temp', u'70000', u'37000'],
         [u'3.0', u'Analog Input 3', u'60000', u'0'],
         [u'4.0', u'Analog Input 4', u'60000', u'0']],
        [[u'48163', u'39158', u'33', u'34']]]


discovery = {'': [('1', {}), ('2', {})]}


checks = {'': [('2',
                {},
                [(1,
                  '[Motor_Temp]: 39.16 V (warn/crit at 37.00 V/70.00 V)',
                  [('voltage', 39.158, 37.0, 70.0, None, None)])]),
               ('1',
                {},
                [(1,
                  '[Tank_Level]: 48.16 V (warn/crit at 10.00 V/80.00 V)',
                  [('voltage', 48.163, 10.0, 80.0, None, None)])])]}
