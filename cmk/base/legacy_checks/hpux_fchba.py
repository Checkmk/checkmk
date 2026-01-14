#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"

# <<<hpux_fchba>>>
# /dev/fcd0
#                        ISP Code version = 4.4.4
#                                Topology = PTTOPT_FABRIC
#             N_Port Port World Wide Name = 0x500143800252658a
#             Switch Port World Wide Name = 0x200400051e6302d7
#                            Driver state = ONLINE
#                        Hardware Path is = 0/0/1/1/0
#          Driver-Firmware Dump Available = NO
# /dev/fcd1
#                        ISP Code version = 4.4.4
#                                Topology = PTTOPT_FABRIC
#             N_Port Port World Wide Name = 0x500143800252658c
#             Switch Port World Wide Name = 0x200400051e5d1942
#                            Driver state = ONLINE
#                        Hardware Path is = 1/0/12/1/0
#          Driver-Firmware Dump Available = NO


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_hpux_fchba(info):
    hbas = {}
    for line in info:
        if line[0].startswith("/dev/"):
            name = line[0][5:]
            hba = {"name": name}
            hbas[name] = hba
        elif len(line) == 2:
            hba[line[0].strip()] = line[1].strip()
    return hbas


def discover_hpux_fchba(section):
    return [(name, None) for name, hba in section.items() if hba["Driver state"] == "ONLINE"]


def check_hpux_fchba(item, _no_params, section):
    if item not in section:
        return (3, "HBA noch found")

    hba = section[item]

    state = 0
    infos = []

    infos.append("Hardware Path: %s" % hba["Hardware Path is"])

    infos.append("Driver State: %s" % hba["Driver state"])
    if hba["Driver state"] != "ONLINE":
        state = 2
        infos[-1] += "(!!)"

    infos.append("Topology: %s" % hba.get("Topology", "(none)"))
    if hba.get("Topology") not in [
        "PTTOPT_FABRIC",
        "PRIVATE_LOOP",
        "PUBLIC_LOOP",
    ]:
        state = 2
        infos[-1] += "(!!)"

    if hba.get("Driver-Firmware Dump Available", "NO") != "NO":
        infos.append("Driver-Firmware Dump Available(!!)")
        state = 2

    return (state, ", ".join(infos))


check_info["hpux_fchba"] = LegacyCheckDefinition(
    name="hpux_fchba",
    service_name="FC HBA %s",
    parse_function=parse_hpux_fchba,
    discovery_function=discover_hpux_fchba,
    check_function=check_hpux_fchba,
)
