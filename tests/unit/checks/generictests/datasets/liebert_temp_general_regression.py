# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_temp_general'


info = [
    [u'Actual Supply Fluid Temp Set Point', u'60.8', u'deg F',
     u'Ambient Air Temperature', u'21.1', u'def C'],
    [u'Free Cooling Utilization', u'0.0',  u'%',
     u'Return Fluid Temperature',  u'62.1',  u'deg F'],
    [u'Supply Fluid Temperature', u'57.2', u'deg F',
     u'Invalid Data for Testsing', u'bogus value', u'Unicycles'],
]


discovery = {'': [(u'Actual Supply Fluid Temp Set Point', {}),
                  (u'Ambient Air Temperature', {}),
                  (u'Free Cooling Utilization', {}),
                  (u'Return Fluid Temperature', {}),
                  (u'Supply Fluid Temperature', {})]}


checks = {'': [(u'Actual Supply Fluid Temp Set Point',
                {},
                [(0, u'16.0 \xb0C', [('temp', 16.0, None, None, None, None)])]),
               (u'Ambient Air Temperature',
                {},
                [(0, u'21.1 \xb0C', [('temp', 21.1, None, None, None, None)])]),
               (u'Free Cooling Utilization',
                {},
                [(0, u'0.0 \xb0C', [('temp', 0.0, None, None, None, None)])]),
               (u'Return Fluid Temperature',
                {},
                [(0,
                  u'16.7 \xb0C',
                  [('temp', 16.722222222222225, None, None, None, None)])]),
               (u'Supply Fluid Temperature',
                {},
                [(0,
                  u'14.0 \xb0C',
                  [('temp', 14.000000000000002, None, None, None, None)])])]}
