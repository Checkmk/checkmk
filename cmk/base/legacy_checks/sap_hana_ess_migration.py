#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="arg-type"

import datetime

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError
from cmk.plugins.sap_hana import lib as sap_hana

check_info = {}

# With reference to SQL sample output (see internal ticket SUP-253)
sap_hana_ess_migration_state_map = {
    "Done (error)": {"cmk_state": 2, "state_readable": "Done with errors."},
    "Installing": {"cmk_state": 1, "state_readable": "Installation in progress."},
    "Done (okay)": {"cmk_state": 0, "state_readable": "Done without errors."},
}


def parse_sap_hana_ess_migration(string_table):
    parsed = {}
    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        if not lines:
            parsed[sid_instance] = {"log": "", "timestamp": "not available"}
            continue

        parsed.setdefault(sid_instance, {"log": " ".join(lines[0]), "timestamp": "not available"})

        for idx, elem in enumerate(lines[0]):
            try:
                timestamp = datetime.datetime.strptime(
                    elem + lines[0][idx + 1], "%Y-%m-%d%H:%M:%S.%f0"
                )
                timestamp_str = datetime.datetime.strftime(timestamp, "%Y-%m-%d %H:%M:%S")
                parsed[sid_instance]["timestamp"] = timestamp_str
            except (ValueError, IndexError):
                pass

    return parsed


def discover_sap_hana_ess_migration(parsed):
    for item in parsed:
        yield item, {}


def check_sap_hana_ess_migration(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    if not data or "log" not in data or not data["log"]:
        raise IgnoreResultsError("Login into database failed.")

    key = None
    for ident in sap_hana_ess_migration_state_map:
        if ident.lower() in data["log"].lower():
            key = ident

    states = sap_hana_ess_migration_state_map.get(
        key, {"cmk_state": 3, "state_readable": "Unknown [%s]" % data["log"]}
    )
    infotext = "ESS State: {} Timestamp: {}".format(states["state_readable"], data["timestamp"])
    yield states["cmk_state"], infotext


check_info["sap_hana_ess_migration"] = LegacyCheckDefinition(
    name="sap_hana_ess_migration",
    parse_function=parse_sap_hana_ess_migration,
    service_name="SAP HANA ESS Migration %s",
    discovery_function=discover_sap_hana_ess_migration,
    check_function=check_sap_hana_ess_migration,
)
