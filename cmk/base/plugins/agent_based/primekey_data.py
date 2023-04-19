#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from enum import Enum
from typing import Mapping

from .agent_based_api.v1 import register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.primekey import DETECT_PRIMEKEY


class Status(Enum):
    OK = 0
    NOT_OK = 1


_Section = Mapping[str, Status]


def parse(string_table: StringTable) -> _Section | None:
    """
    >>> parse([['0','1','0','0','1']])
    {'VMs': <Status.OK: 0>, 'RAID': <Status.NOT_OK: 1>, 'EJBCA': <Status.OK: 0>, 'Signserver': <Status.OK: 0>, 'HSM': <Status.NOT_OK: 1>}
    """
    if not string_table:
        return None
    item_names = ["VMs", "RAID", "EJBCA", "Signserver", "HSM"]
    return dict(zip(item_names, [Status(int(i)) for i in string_table[0]]))


register.snmp_section(
    name="primekey_data",
    parse_function=parse,
    detect=DETECT_PRIMEKEY,
    fetch=SNMPTree(
        ".1.3.6.1.4.1.22408.1.1.2",
        [
            "1.2.118.109.1",  # VMs
            "1.5.114.97.105.100.49.1",  # RAID
            "1.8.104.101.97.108.116.104.101.50.1",  # EJBCA
            "1.8.104.101.97.108.116.104.115.50.1",  # Signserver
            "2.4.104.115.109.51.1",  # HSM
        ],
    ),
)


def discover(section: _Section) -> DiscoveryResult:
    for item in section.keys():
        yield Service(item=item)


def check(
    item: str,
    section: _Section,
) -> CheckResult:
    """
    >>> list(check('VMs', {'VMs': Status.OK, 'RAID': Status.NOT_OK, 'EJBCA': Status.OK, 'Signserver': Status.OK, 'HSM': Status.NOT_OK}))
    [Result(state=<State.OK: 0>, notice='Status is ok')]
    >>> list(check('RAID', {'VMs': Status.OK, 'RAID': Status.NOT_OK, 'EJBCA': Status.OK, 'Signserver': Status.OK, 'HSM': Status.NOT_OK}))
    [Result(state=<State.CRIT: 2>, summary='Status is not ok')]
    """
    if not (status := section.get(item)):
        return

    if status is Status.OK:
        yield Result(state=State.OK, notice="Status is ok")
    else:
        yield Result(state=State.CRIT, notice="Status is not ok")


register.check_plugin(
    name="primekey_data",
    service_name="PrimeKey %s Status",
    discovery_function=discover,
    check_function=check,
)
