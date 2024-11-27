#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.plugins.lib import ucs_bladecenter

check_info = {}

# <<<ucs_bladecenter_faultinst:sep(9)>>>
# faultInst   Dn sys/chassis-2/bl...ault-F1256 Descr Local disk 2 missing on server 2/3    Severity info
# faultInst   Dn sys/chassis-2/bl...ault-F1256 Descr Local disk 1 missing on server 2/3    Severity info
# faultInst   Dn sys/chassis-1/bl...ault-F1256 Descr Local disk 2 missing on server 1/3    Severity info


def inventory_ucs_bladecenter_faultinst(parsed):
    yield None, None


def check_ucs_bladecenter_faultinst(_item, params, parsed):
    severities = {}
    for values in parsed.get("faultInst", {}).values():
        entry_sev = values.get("Severity").lower()
        severities.setdefault(entry_sev, [])
        severities[entry_sev].append(values)

    if not severities:
        yield 0, "No fault instances found"
        return

    for sev, instances in severities.items():
        sev_state = params.get(sev, ucs_bladecenter.UCS_FAULTINST_SEVERITY_TO_STATE.get(sev, 3))

        # Right now, OK instances are also reported in detail
        # If required we can increase the state level here, so that only WARN+ messages are shown
        if sev_state >= 0:
            extra_info = []
            for instance in instances:
                extra_info.append("%s" % instance["Descr"])
            extra_info_str = ": " + ", ".join(extra_info)
        else:
            extra_info_str = ""

        yield sev_state, "%d %s Instances%s" % (len(instances), sev.upper(), extra_info_str)


check_info["ucs_bladecenter_faultinst"] = LegacyCheckDefinition(
    name="ucs_bladecenter_faultinst",
    parse_function=ucs_bladecenter.generic_parse,
    service_name="Fault Instances Blade",
    discovery_function=inventory_ucs_bladecenter_faultinst,
    check_function=check_ucs_bladecenter_faultinst,
    check_ruleset_name="ucs_bladecenter_faultinst",
)
