# -*- encoding: utf-8
# yapf: disable


checkname = u'citrix_controller'


info = [[u'ControllerState'],
        [u'ControllerVersion'],
        [u'DesktopsRegistered'],
        [u'LicensingServerState'],
        [u'LicensingGraceState'],
        [u'ActiveSiteServices'],
        [u'TotalFarmActiveSessions', u'0'],
        [u'TotalFarmInactiveSessions', u'0']]


discovery = {'': [(None, None)],
             'licensing': [(None, None)],
             'registered': [(None, None)],
             'services': [(None, None)],
             'sessions': [(None, {})]}


checks = {'': [(None, {}, [(3, 'unknown', [])])],
          'licensing': [(None, {}, [])],
          'registered': [(None, {}, [(3, 'No desktops registered', [])])],
          'services': [(None, {}, [(0, '', [])])],
          'sessions': [(None,
                        {},
                        [(0,
                          'total: 0, active: 0, inactive: 0',
                          [('total_sessions', 0, None, None, None, None),
                           ('active_sessions', 0, None, None, None, None),
                           ('inactive_sessions', 0, None, None, None, None)])])]}