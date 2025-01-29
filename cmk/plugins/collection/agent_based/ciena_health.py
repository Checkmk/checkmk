#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Generic, TypeVar

from cmk.agent_based.v2 import (
    CheckPlugin,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.ciena_ces import (
    DETECT_CIENA_5142,
    DETECT_CIENA_5171,
    FanStatus,
    LeoFanStatus,
    LeoPowerSupplyState,
    LeoSystemState,
    PowerSupplyState,
    SNMPEnum,
    TceHealthStatus,
)

SNMPDataTypeVar = TypeVar("SNMPDataTypeVar", bound=SNMPEnum)


@dataclasses.dataclass(frozen=True)
class SNMPData(Generic[SNMPDataTypeVar]):
    display_name: str
    data_type: type[SNMPDataTypeVar]
    occurences: Mapping[SNMPDataTypeVar, int]


Section = Sequence[SNMPData]


def discover_ciena_health(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


CheckResultCienaHealth = Iterable[Result]


def _summarize_discrete_snmp_values(
    data: SNMPData,
) -> CheckResultCienaHealth:
    """Many SNMP devices deliver a collection of discrete values such as this
        INTEGER {normal(1), warning(2), degraded(3), faulted(4)}
    for a number of objects, e.g. fans. The goal of this function is summarize such a collection of
    values into two Result 's. The information from the MIB (which tells us how the values are
    encoded) is encoded by an enum.
    """
    name = data.display_name
    good_value = data.data_type.good_value()
    num_total = sum(data.occurences.values())
    details = f"{num_total} {name} | "
    details += ", ".join(f"{status.name} : {data.occurences[status]}" for status in data.data_type)
    all_good = num_total == data.occurences[good_value]
    yield Result(
        state=State.OK if all_good else State.CRIT,
        summary=f"{num_total} {name}, {'all' if all_good else 'some not'} {good_value.name}",
        details=details,
    )


def check_ciena_health(section: Section) -> CheckResultCienaHealth:
    for data in section:
        yield from _summarize_discrete_snmp_values(data)


check_plugin_ciena_health = CheckPlugin(
    name="ciena_health",
    service_name="Health",
    discovery_function=discover_ciena_health,
    check_function=check_ciena_health,
)


_REFERENCES_5142 = [
    ("memory state(s)", LeoSystemState),
    ("power supplies", LeoPowerSupplyState),
    ("tmpfs", LeoSystemState),
    ("sysfs", LeoSystemState),
    ("fan(s)", LeoFanStatus),
]

_REFERENCES_5171 = [
    ("memory state(s)", TceHealthStatus),
    ("power supplies", PowerSupplyState),
    ("CPU health", TceHealthStatus),
    ("disk(s)", TceHealthStatus),
    ("fan(s)", FanStatus),
]


def parse_ciena_health(
    references: Iterable[tuple[str, type[SNMPEnum]]], string_table: Sequence[StringTable]
) -> Section:
    return [
        SNMPData(display_name, data_type, data)
        for (display_name, data_type), table in zip(references, string_table)
        if (data := Counter(data_type(entry) for row in table for entry in row))
    ]


def make_parse_function(
    references: Iterable[tuple[str, type[SNMPEnum]]],
) -> Callable[[Sequence[StringTable]], Section]:
    def parse(string_table: Sequence[StringTable]) -> Section:
        return parse_ciena_health(references, string_table)

    return parse


snmp_section_ciena_health_5142 = SNMPSection(
    name="ciena_health_5142",
    parsed_section_name="ciena_health",
    parse_function=make_parse_function(_REFERENCES_5142),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.6141.2.60",
            oids=[
                "12.1.13.7",  # wwpLeosSystemMemoryUtilizationAvailableMemoryState
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.6141.2.60",
            oids=[
                "11.1.1.3.1.1.2",  # wwpLeosChassisPowerSupplyState
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.6141.2.60",
            oids=[
                "12.1.12.4",  # wwpLeosSystemFileSystemUtilizationTmpfsState
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.6141.2.60",
            oids=[
                "12.1.12.8",  # wwpLeosSystemFileSystemUtilizationSysfsState
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.6141.2.60",
            oids=[
                "11.1.1.4.1.1.3",  # wwpLeosChassisFanModuleStatus
            ],
        ),
    ],
    detect=DETECT_CIENA_5142,
)

snmp_section_ciena_health_5171 = SNMPSection(
    name="ciena_health_5171",
    parsed_section_name="ciena_health",
    parse_function=make_parse_function(_REFERENCES_5171),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1271.2.1.5.1.2.1",
            oids=[
                "4.24.1.3",  # cienaCesChassisMemoryHealthState
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1271.2.1.5.1.2.1",
            oids=[
                "1.1.1.2",  # cienaCesChassisPowerSupplyState
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1271.2.1.5.1.2.1",
            oids=[
                "4.5.1.3",  # cienaCesChassisCPUHealthState
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1271.2.1.5.1.2.1",
            oids=[
                "4.12.1.3",  # cienaCesChassisDiskHealthState
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1271.2.1.5.1.2.1",
            oids=[
                "2.1.1.3",  # cienaCesChassisFanStatus
            ],
        ),
    ],
    detect=DETECT_CIENA_5171,
)
