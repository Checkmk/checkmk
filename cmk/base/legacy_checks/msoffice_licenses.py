#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<msoffice_licenses>>>
# msonline:VISIOCLIENT 11 0 10
# msonline:POWER_BI_PRO 13 0 11
# msonline:WINDOWS_STORE 1000000 0 0
# msonline:ENTERPRISEPACK 1040 1 395
# msonline:FLOW_FREE 10000 0 11
# msonline:EXCHANGESTANDARD 5 0 2
# msonline:POWER_BI_STANDARD 1000000 0 18
# msonline:EMS 1040 0 991
# msonline:RMSBASIC 1 0 0
# msonline:PROJECTPROFESSIONAL 10 0 10
# msonline:ATP_ENTERPRISE 1040 0 988


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render

check_info = {}


def parse_msoffice_licenses(string_table):
    parsed = {}

    for line in string_table:
        if len(line) != 4:
            continue

        try:
            parsed.setdefault(
                line[0],
                {"active": int(line[1]), "warning_units": int(line[2]), "consumed": int(line[3])},
            )
        except ValueError:
            pass

    return parsed


def check_msoffice_licenses(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return
    lcs_active = item_data["active"]
    lcs_consumed = item_data["consumed"]

    if lcs_active:
        warn, crit = params["usage"]
        warn_abs, crit_abs = None, None
        warn_perc, crit_perc = None, None
        if isinstance(warn, float):
            warn_perc, crit_perc = warn, crit
        else:
            warn_abs, crit_abs = warn, crit

        # the agent plug-in also gathers the last 3 unused licenses with no
        # active licenses. To handle this, we only output consumed licenses for
        # licenses with active ones
        yield check_levels(
            lcs_consumed,
            "licenses",
            (warn_abs, crit_abs),
            human_readable_func=int,
            infoname="Consumed licenses",
        )

        yield (
            0,
            "Active licenses: %s" % lcs_active,
            [("licenses_total", lcs_active)],
        )

        usage = lcs_consumed * 100.0 / (lcs_active)
        yield check_levels(
            usage,
            "license_percentage",
            (warn_perc, crit_perc),
            human_readable_func=render.percent,
            infoname="Usage",
            boundaries=(0, 100),
        )

    else:
        yield 0, "No active licenses"
        return

    lcs_warning_units = item_data["warning_units"]
    if lcs_warning_units:
        yield 0, " Warning units: %s" % lcs_warning_units


def discover_msoffice_licenses(section):
    yield from ((item, {}) for item in section)


check_info["msoffice_licenses"] = LegacyCheckDefinition(
    name="msoffice_licenses",
    parse_function=parse_msoffice_licenses,
    service_name="MS Office Licenses %s",
    discovery_function=discover_msoffice_licenses,
    check_function=check_msoffice_licenses,
    check_ruleset_name="msoffice_licenses",
    check_default_parameters={
        "usage": (80.0, 90.0),
    },
)
