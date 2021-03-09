# -*- encoding: utf-8
# yapf: disable


checkname = u'akcp_sensor_humidity'


info = [[u'Humidity1 Description', u'', u'7', u'1'],
        [u'Humidity2 Description', u'', u'0', u'2']]


discovery = {'': [(u'Humidity1 Description', 'akcp_humidity_defaultlevels')]}


checks = {'': [(u'Humidity1 Description',
                (30, 35, 60, 65),
                [(2, 'State: sensor error', [])])]}