# -*- encoding: utf-8
# yapf: disable


checkname = u'citrix_controller'


info = [[u'ControllerState', u'Active'],
        [u'ControllerVersion', u'7.6.0.5024'],
        [u'DesktopsRegistered', u'29'],
        [u'LicensingServerState', u'OK'],
        [u'LicensingGraceState', u'NotActive'],
        [u'ActiveSiteServices', u'XenPool01', u'-', u'Cisco', u'UCS', u'VMware'],
        [u'TotalFarmActiveSessions', u'262'],
        [u'TotalFarmInactiveSessions', u'14']]


discovery = {'': [(None, None)],
             'licensing': [(None, None)],
             'registered': [(None, None)],
             'services': [(None, None)],
             'sessions': [(None, {})]}


checks = {'': [(None, {}, [(0, u'Active', [])])],
          'licensing': [(None,
                         {},
                         [(0, 'Licensing Server State: OK', []),
                          (0, 'Licensing Grace State: not active', [])])],
          'registered': [(None,
                          {},
                          [(0,
                            '29',
                            [('registered_desktops', 29, None, None, None, None)])])],
          'services': [(None, {}, [(0, u'XenPool01 - Cisco UCS VMware', [])])],
          'sessions': [(None,
                        {},
                        [(0,
                          'total: 276, active: 262, inactive: 14',
                          [('total_sessions', 276, None, None, None, None),
                           ('active_sessions', 262, None, None, None, None),
                           ('inactive_sessions', 14, None, None, None, None)])])]}