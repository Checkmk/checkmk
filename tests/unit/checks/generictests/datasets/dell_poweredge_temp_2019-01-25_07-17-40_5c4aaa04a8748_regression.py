# -*- encoding: utf-8
# yapf: disable


checkname = u'dell_poweredge_temp'


info = [[u'1',
         u'1',
         u'2',
         u'3',
         u'170',
         u'System Board Inlet Temp',
         u'470',
         u'420',
         u'30',
         u'-70'],
        [u'1',
         u'2',
         u'2',
         u'3',
         u'300',
         u'System Board Exhaust Temp',
         u'750',
         u'700',
         u'80',
         u'30'],
        [u'1', u'3', u'1', u'2', u'', u'CPU1 Temp', u'', u'', u'', u''],
        [u'1', u'4', u'1', u'2', u'', u'CPU2 Temp', u'', u'', u'', u'']]


discovery = {'': [(u'System Board Exhaust', {}), (u'System Board Inlet', {})]}


checks = {'': [(u'System Board Exhaust',
                {},
                [(0, u'30.0 \xb0C', [('temp', 30.0, 70.0, 75.0, None, None)])]),
               (u'System Board Inlet',
                {},
                [(0, u'17.0 \xb0C', [('temp', 17.0, 42.0, 47.0, None, None)])])]}