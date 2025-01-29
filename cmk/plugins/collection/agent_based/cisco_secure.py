#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def _sanitize_mac(string):
    hx_gen = ("%02s" % hex(ord(m))[2:] for m in string)
    return ":".join(hx_gen).replace(" ", "0")


Section = Sequence


def parse_cisco_secure(string_table: Sequence[StringTable]) -> Section:
    parsed = []
    # l[1] = Name, l[2] = Portstate
    names = {l[0]: (l[1], l[2]) for l in string_table[0]}
    for num, is_enabled, status, violation_count, lastmac in string_table[1]:
        mac = _sanitize_mac(lastmac)
        enabled_txt = {"1": "yes", "2": "no"}.get(is_enabled)
        try:
            status_int = int(status)
        except ValueError:
            status_int = None
        # violationCount is initialized with 0 when security is enabled. When not, the
        # value is reported as empty string. saveint() makes life easier here.
        if num in names:
            parsed.append(
                (
                    names[num][0],
                    int(names[num][1]),
                    enabled_txt,
                    status_int,
                    saveint(violation_count),
                    mac,
                )
            )
        else:
            parsed.append((num, 0, enabled_txt, status_int, saveint(violation_count), mac))

    return parsed


def inventory_cisco_secure(section: Section) -> DiscoveryResult:
    # search for at least one port with security
    for _name, op_state, is_enabled, status, _violation_count, _lastmac in section:
        # if portsecurity enabled and port up OR currently there is sercurity issue`
        if status == 3 or (is_enabled != "no" and op_state == 1):
            yield Service()


def check_cisco_secure(section: Section) -> CheckResult:
    secure_states = {
        1: "full Operational",
        2: "could not be enabled due to certain reasons",
        3: "shutdown due to security violation",
    }

    at_least_one_problem = False
    for name, op_state, is_enabled, status, violation_count, lastmac in section:
        message = "Port %s: %s (violation count: %d, last MAC: %s)" % (
            name,
            secure_states.get(status, "unknown"),
            violation_count,
            lastmac,
        )

        if is_enabled is not None:
            # If port cant be enabled and is up and has violations -> WARN
            if status == 2 and op_state == 1 and violation_count > 0:
                yield Result(state=State.WARN, summary=message)
                at_least_one_problem = True
            # Security issue -> CEIT
            elif status == 3:
                yield Result(state=State.CRIT, summary=message)
                at_least_one_problem = True
            elif status is None:
                yield Result(state=State.UNKNOWN, summary=message)
                at_least_one_problem = True
        else:
            yield Result(state=State.UNKNOWN, summary=message + " unknown enabled state")
            at_least_one_problem = True

    if not at_least_one_problem:
        yield Result(state=State.OK, summary="No port security violation")


snmp_section_cisco_secure = SNMPSection(
    name="cisco_secure",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), exists(".1.3.6.1.4.1.9.9.315.1.2.1.1.1.*")
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[OIDEnd(), "2", "8"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.315.1.2.1.1",
            oids=[OIDEnd(), "1", "2", "9", "10"],
        ),
    ],
    parse_function=parse_cisco_secure,
)


check_plugin_cisco_secure = CheckPlugin(
    name="cisco_secure",
    service_name="Port Security",
    discovery_function=inventory_cisco_secure,
    check_function=check_cisco_secure,
)
