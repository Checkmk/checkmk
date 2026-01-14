#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_salesforce(string_table):
    import json

    pre_parsed = []
    for line in string_table:
        pre_parsed.append(json.loads(" ".join(line)))

    parsed = {}
    for entry in pre_parsed:
        if entry.get("key"):
            parsed.setdefault(entry.get("key"), entry)
    return parsed


def discover_salesforce_instances(parsed):
    for instance, attrs in parsed.items():
        if attrs.get("isActive"):
            yield instance, {}


def check_salesforce_instances(item, params, parsed):
    map_states = {
        "OK": (0, "OK"),
        "MAJOR_INCIDENT_CORE": (2, "major incident core"),
        "MINOR_INCIDENT_CORE": (1, "minor incident core"),
        "MAINTENANCE_CORE": (0, "maintenance core"),
        "INFORMATIONAL_CORE": (0, "informational core"),
        "MAJOR_INCIDENT_NONCORE": (2, "major incident noncore"),
        "MINOR_INCIDENT_NONCORE": (1, "minor incident noncore"),
        "MAINTENANCE_NONCORE": (0, "maintenance noncore"),
        "INFORMATIONAL_NONCORE": (0, "informational noncore"),
    }

    if item in parsed:
        data = parsed[item]
        status = data.get("status")
        state, state_readable = map_states.get(status, (3, "unknown[%s]" % status))
        yield state, "Status: %s" % state_readable

        for key, title in [
            ("environment", "Environment"),
            ("releaseNumber", "Release Number"),
            ("releaseVersion", "Release Version"),
        ]:
            if data.get(key):
                yield 0, f"{title}: {data[key]}"


check_info["salesforce_instances"] = LegacyCheckDefinition(
    name="salesforce_instances",
    parse_function=parse_salesforce,
    service_name="Salesforce Instance %s",
    discovery_function=discover_salesforce_instances,
    check_function=check_salesforce_instances,
)
