#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "citrix_controller"


info = [
    ["ControllerState", "Active"],
    ["ControllerVersion", "7.18.0.21"],
    ["DesktopsRegistered", "13"],
    ["LicensingServerState", "OK"],
    ["LicensingGraceState", "Expired"],
    [
        "ActiveSiteServices",
        "ControllerReaper",
        "ControllerNameCacheRefresh",
        "Licensing",
        "BrokerReaper",
        "RegistrationHardening",
        "WorkerNameCacheRefresh",
        "AccountNameCacheRefresh",
        "PowerPolicy",
        "GroupUsage",
        "AddressNameResolver",
        "RebootScheduleManager",
        "RebootCycleManager",
        "ScopeNamesRefresh",
        "FeatureChecks",
        "RemotePC",
        "IdleSessionManager",
        "OperationalEventsService",
        "ConfigurationExport",
        "LicenseTypeChanged",
    ],
    ["TotalFarmActiveSessions", "128"],
    ["TotalFarmInactiveSessions", "13"],
    ["ControllerState", "Active"],
    ["ControllerVersion", "7.18.0.21"],
    ["DesktopsRegistered", "13"],
    ["LicensingServerState", "OK"],
    ["LicensingGraceState", "Expired"],
    [
        "ActiveSiteServices",
        "ControllerReaper",
        "ControllerNameCacheRefresh",
        "Licensing",
        "BrokerReaper",
        "RegistrationHardening",
        "WorkerNameCacheRefresh",
        "AccountNameCacheRefresh",
        "PowerPolicy",
        "GroupUsage",
        "AddressNameResolver",
        "RebootScheduleManager",
        "RebootCycleManager",
        "ScopeNamesRefresh",
        "FeatureChecks",
        "RemotePC",
        "IdleSessionManager",
        "OperationalEventsService",
        "ConfigurationExport",
        "LicenseTypeChanged",
    ],
    ["TotalFarmActiveSessions", "128"],
    ["TotalFarmInactiveSessions", "13"],
]


discovery = {
    "": [(None, None)],
    "licensing": [(None, None)],
    "registered": [(None, None)],
    "services": [(None, None)],
    "sessions": [(None, {})],
}


checks = {
    "": [(None, {}, [(0, "Active", [])])],
    "licensing": [
        (
            None,
            {},
            [(0, "Licensing Server State: OK", []), (2, "Licensing Grace State: expired", [])],
        )
    ],
    "registered": [(None, {}, [(0, "13", [("registered_desktops", 13, None, None, None, None)])])],
    "services": [
        (
            None,
            {},
            [
                (
                    0,
                    "ControllerReaper ControllerNameCacheRefresh Licensing BrokerReaper RegistrationHardening WorkerNameCacheRefresh AccountNameCacheRefresh PowerPolicy GroupUsage AddressNameResolver RebootScheduleManager RebootCycleManager ScopeNamesRefresh FeatureChecks RemotePC IdleSessionManager OperationalEventsService ConfigurationExport LicenseTypeChanged",
                    [],
                )
            ],
        )
    ],
    "sessions": [
        (
            None,
            {},
            [
                (
                    0,
                    "total: 141, active: 128, inactive: 13",
                    [
                        ("total_sessions", 141, None, None, None, None),
                        ("active_sessions", 128, None, None, None, None),
                        ("inactive_sessions", 13, None, None, None, None),
                    ],
                )
            ],
        )
    ],
}
