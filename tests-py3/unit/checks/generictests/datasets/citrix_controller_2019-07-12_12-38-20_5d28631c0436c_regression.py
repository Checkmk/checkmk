#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'citrix_controller'


info = [[u'ControllerState', u'Active'],
        [u'ControllerVersion', u'7.18.0.21'],
        [u'DesktopsRegistered', u'13'],
        [u'LicensingServerState', u'OK'],
        [u'LicensingGraceState', u'Expired'],
        [u'ActiveSiteServices',
         u'ControllerReaper',
         u'ControllerNameCacheRefresh',
         u'Licensing',
         u'BrokerReaper',
         u'RegistrationHardening',
         u'WorkerNameCacheRefresh',
         u'AccountNameCacheRefresh',
         u'PowerPolicy',
         u'GroupUsage',
         u'AddressNameResolver',
         u'RebootScheduleManager',
         u'RebootCycleManager',
         u'ScopeNamesRefresh',
         u'FeatureChecks',
         u'RemotePC',
         u'IdleSessionManager',
         u'OperationalEventsService',
         u'ConfigurationExport',
         u'LicenseTypeChanged'],
        [u'TotalFarmActiveSessions', u'128'],
        [u'TotalFarmInactiveSessions', u'13'],
        [u'ControllerState', u'Active'],
        [u'ControllerVersion', u'7.18.0.21'],
        [u'DesktopsRegistered', u'13'],
        [u'LicensingServerState', u'OK'],
        [u'LicensingGraceState', u'Expired'],
        [u'ActiveSiteServices',
         u'ControllerReaper',
         u'ControllerNameCacheRefresh',
         u'Licensing',
         u'BrokerReaper',
         u'RegistrationHardening',
         u'WorkerNameCacheRefresh',
         u'AccountNameCacheRefresh',
         u'PowerPolicy',
         u'GroupUsage',
         u'AddressNameResolver',
         u'RebootScheduleManager',
         u'RebootCycleManager',
         u'ScopeNamesRefresh',
         u'FeatureChecks',
         u'RemotePC',
         u'IdleSessionManager',
         u'OperationalEventsService',
         u'ConfigurationExport',
         u'LicenseTypeChanged'],
        [u'TotalFarmActiveSessions', u'128'],
        [u'TotalFarmInactiveSessions', u'13']]


discovery = {'': [(None, None)],
             'licensing': [(None, None)],
             'registered': [(None, None)],
             'services': [(None, None)],
             'sessions': [(None, {})]}


checks = {'': [(None, {}, [(0, u'Active', [])])],
          'licensing': [(None,
                         {},
                         [(0, 'Licensing Server State: OK', []),
                          (2, 'Licensing Grace State: expired', [])])],
          'registered': [(None,
                          {},
                          [(0,
                            '13',
                            [('registered_desktops', 13, None, None, None, None)])])],
          'services': [(None,
                        {},
                        [(0,
                          u'ControllerReaper ControllerNameCacheRefresh Licensing BrokerReaper RegistrationHardening WorkerNameCacheRefresh AccountNameCacheRefresh PowerPolicy GroupUsage AddressNameResolver RebootScheduleManager RebootCycleManager ScopeNamesRefresh FeatureChecks RemotePC IdleSessionManager OperationalEventsService ConfigurationExport LicenseTypeChanged',
                          [])])],
          'sessions': [(None,
                        {},
                        [(0,
                          'total: 141, active: 128, inactive: 13',
                          [('total_sessions', 141, None, None, None, None),
                           ('active_sessions', 128, None, None, None, None),
                           ('inactive_sessions', 13, None, None, None, None)])])]}
