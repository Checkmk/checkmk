#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# .
#   .--Status--------------------------------------------------------------.
#   |                    ____  _        _                                  |
#   |                   / ___|| |_ __ _| |_ _   _ ___                      |
#   |                   \___ \| __/ _` | __| | | / __|                     |
#   |                    ___) | || (_| | |_| |_| \__ \                     |
#   |                   |____/ \__\__,_|\__|\__,_|___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, exists, SNMPTree, StringTable

check_info = {}


def discover_entersekt(info):
    if info:
        yield None, {}


def check_entersekt_status(item, params, info):
    status = 3
    infotext = "Item not found in SNMP output"
    if info[0][0] == "true":
        status = 0
        infotext = "Server is running"
    else:
        status = 2
        infotext = "Server is NOT running"
    yield int(status), infotext


def parse_entersekt(string_table: StringTable) -> StringTable:
    return string_table


check_info["entersekt"] = LegacyCheckDefinition(
    name="entersekt",
    parse_function=parse_entersekt,
    detect=all_of(contains(".1.3.6.1.2.1.1.1.0", "linux"), exists(".1.3.6.1.4.1.38235.2.3.1.0")),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.38235.2",
        oids=["3.1.0", "3.4.0", "3.8.0", "3.9.0", "17.1.0"],
    ),
    service_name="Entersekt Server Status",
    discovery_function=discover_entersekt,
    check_function=check_entersekt_status,
)


# .
#   .--Http EmrErrors------------------------------------------------------.
#   |                         _   _ _   _                                  |
#   |                        | | | | |_| |_ _ __                           |
#   |                        | |_| | __| __| '_ \                          |
#   |                        |  _  | |_| |_| |_) |                         |
#   |                        |_| |_|\__|\__| .__/                          |
#   |                                      |_|                             |
#   |         _____                _____                                   |
#   |        | ____|_ __ ___  _ __| ____|_ __ _ __ ___  _ __ ___           |
#   |        |  _| | '_ ` _ \| '__|  _| | '__| '__/ _ \| '__/ __|          |
#   |        | |___| | | | | | |  | |___| |  | | | (_) | |  \__ \          |
#   |        |_____|_| |_| |_|_|  |_____|_|  |_|  \___/|_|  |___/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
def discover_entersekt_emrerrors(info):
    if info:
        yield None, {}


def check_entersekt_emrerrors(item, params, info):
    if params:
        (warn, crit) = params["levels"]
    else:
        (warn, crit) = (100, 200)
    status = 3
    infotext = "Item not found in SNMP output"
    if int(info[0][1]) > crit:
        status = 2
        infotext = f"Number of errors is {int(info[0][1])} which is higher than {crit}"
    elif int(info[0][1]) > warn:
        status = 1
        infotext = f"Number of errors is {int(info[0][1])} which is higher than {warn}"
    else:
        status = 0
        infotext = "Number of errors is %s " % (info[0][1])
    perfdata = [("Errors", int(info[0][1]), warn, crit)]
    yield int(status), infotext, perfdata


check_info["entersekt.emrerrors"] = LegacyCheckDefinition(
    name="entersekt_emrerrors",
    service_name="Entersekt http EMR Errors",
    sections=["entersekt"],
    discovery_function=discover_entersekt_emrerrors,
    check_function=check_entersekt_emrerrors,
    check_ruleset_name="entersekt_emrerrors",
)

# .
#   .--sgHttp EcertErrors--------------------------------------------------.
#   |                              _   _ _   _                             |
#   |                    ___  __ _| | | | |_| |_ _ __                      |
#   |                   / __|/ _` | |_| | __| __| '_ \                     |
#   |                   \__ \ (_| |  _  | |_| |_| |_) |                    |
#   |                   |___/\__, |_| |_|\__|\__| .__/                     |
#   |                        |___/              |_|                        |
#   |        _____              _   _____                                  |
#   |       | ____|___ ___ _ __| |_| ____|_ __ _ __ ___  _ __ ___          |
#   |       |  _| / __/ _ \ '__| __|  _| | '__| '__/ _ \| '__/ __|         |
#   |       | |__| (_|  __/ |  | |_| |___| |  | | | (_) | |  \__ \         |
#   |       |_____\___\___|_|   \__|_____|_|  |_|  \___/|_|  |___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_entersekt_ecerterrors(info):
    if info:
        yield None, {}


def check_entersekt_ecerterrors(item, params, info):
    if params:
        (warn, crit) = params["levels"]
    else:
        (warn, crit) = (100, 200)
    status = 3
    infotext = "Item not found in SNMP output"
    if int(info[0][2]) > crit:
        status = 2
        infotext = f"Number of errors is {int(info[0][2])} which is higher than {crit}"
    elif int(info[0][2]) > warn:
        status = 1
        infotext = f"Number of errors is {int(info[0][2])} which is higher than {warn}"
    else:
        status = 0
        infotext = "Number of errors is %s " % (info[0][2])
    perfdata = [("Errors", int(info[0][2]), warn, crit)]
    yield int(status), infotext, perfdata


check_info["entersekt.ecerterrors"] = LegacyCheckDefinition(
    name="entersekt_ecerterrors",
    service_name="Entersekt http Ecert Errors",
    sections=["entersekt"],
    discovery_function=discover_entersekt_ecerterrors,
    check_function=check_entersekt_ecerterrors,
    check_ruleset_name="entersekt_ecerterrors",
)


# .
#   .--Soap Service Errors-------------------------------------------------.
#   |     ____                      ____                  _                |
#   |    / ___|  ___   __ _ _ __   / ___|  ___ _ ____   _(_) ___ ___       |
#   |    \___ \ / _ \ / _` | '_ \  \___ \ / _ \ '__\ \ / / |/ __/ _ \      |
#   |     ___) | (_) | (_| | |_) |  ___) |  __/ |   \ V /| | (_|  __/      |
#   |    |____/ \___/ \__,_| .__/  |____/ \___|_|    \_/ |_|\___\___|      |
#   |                      |_|                                             |
#   |                    _____                                             |
#   |                   | ____|_ __ _ __ ___  _ __ ___                     |
#   |                   |  _| | '__| '__/ _ \| '__/ __|                    |
#   |                   | |___| |  | | | (_) | |  \__ \                    |
#   |                   |_____|_|  |_|  \___/|_|  |___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
def discover_entersekt_soaperrors(info):
    if info:
        yield None, {}


def check_entersekt_soaperrors(_no_item, params, info):
    yield check_levels(
        value=int(info[0][3]),
        dsname="Errors",
        params=params["levels"],
        human_readable_func=str,
        infoname="Number of errors",
    )


check_info["entersekt.soaperrors"] = LegacyCheckDefinition(
    name="entersekt_soaperrors",
    service_name="Entersekt Soap Service Errors",
    sections=["entersekt"],
    discovery_function=discover_entersekt_soaperrors,
    check_function=check_entersekt_soaperrors,
    check_ruleset_name="entersekt_soaperrors",
)

# .
#   .--sgConsoleDaysToNextCertExpiry---------------------------------------.
#   |             ____                      _      ____                    |
#   |  ___  __ _ / ___|___  _ __  ___  ___ | | ___|  _ \  __ _ _   _ ___   |
#   | / __|/ _` | |   / _ \| '_ \/ __|/ _ \| |/ _ \ | | |/ _` | | | / __|  |
#   | \__ \ (_| | |__| (_) | | | \__ \ (_) | |  __/ |_| | (_| | |_| \__ \  |
#   | |___/\__, |\____\___/|_| |_|___/\___/|_|\___|____/ \__,_|\__, |___/  |
#   |      |___/                                               |___/       |
#   |  _____     _   _           _    ____          _   _____              |
#   | |_   _|__ | \ | | _____  _| |_ / ___|___ _ __| |_| ____|_  ___ __    |
#   |   | |/ _ \|  \| |/ _ \ \/ / __| |   / _ \ '__| __|  _| \ \/ / '_ \   |
#   |   | | (_) | |\  |  __/>  <| |_| |__|  __/ |  | |_| |___ >  <| |_) |  |
#   |   |_|\___/|_| \_|\___/_/\_\\__|\____\___|_|   \__|_____/_/\_\ .__/   |
#   |                                                             |_|      |
#   |                            _                                         |
#   |                           (_)_ __ _   _                              |
#   |                           | | '__| | | |                             |
#   |                           | | |  | |_| |                             |
#   |                           |_|_|   \__, |                             |
#   |                                   |___/                              |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_entersekt_certexpiry(info):
    if info:
        yield None, {}


def check_entersekt_certexpiry(item, params, info):
    if params:
        (warn, crit) = params["levels"]
    else:
        (warn, crit) = (20, 10)
    status = 3
    infotext = "Item not found in SNMP output"
    if int(info[0][4]) < warn:
        status = 1
        infotext = f"Number of days until expiration is {int(info[0][4])} which is less than {warn}"
        if int(info[0][4]) < crit:
            status = 2
            infotext = (
                f"Number of days until expiration is {int(info[0][4])} which is less than {crit}"
            )
    else:
        status = 0
        infotext = "Number of days is %s " % (info[0][4])
    perfdata = [("Days", int(info[0][4]), warn, crit)]
    yield int(status), infotext, perfdata


check_info["entersekt.certexpiry"] = LegacyCheckDefinition(
    name="entersekt_certexpiry",
    service_name="Entersekt Certificate Expiration",
    sections=["entersekt"],
    discovery_function=discover_entersekt_certexpiry,
    check_function=check_entersekt_certexpiry,
    check_ruleset_name="entersekt_certexpiry",
)
