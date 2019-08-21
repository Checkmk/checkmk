# -*- encoding: utf-8
# yapf: disable


checkname = 'lnx_thermal'


info = [[u'thermal_zone0',
         u'enabled',
         u'acpitz',
         u'27800',
         u'105000',
         u'critical',
         u'80000',
         u'active',
         u'55000',
         u'active',
         u'500',
         u'00',
         u'active',
         u'45000',
         u'active',
         u'40000',
         u'active'],
        [u'thermal_zone1',
         u'enabled',
         u'acpitz',
         u'29800',
         u'105000',
         u'critical',
         u'108000',
         u'passive']]


discovery = {'': [(u'Zone 1', {})]}


checks = {'': [(u'Zone 1',
                {'device_levels_handling': 'devdefault', 'levels': (70.0, 80.0)},
                [(0, u'29.8 \xb0C', [('temp', 29.8, 108.0, 105.0, None, None)])])]}