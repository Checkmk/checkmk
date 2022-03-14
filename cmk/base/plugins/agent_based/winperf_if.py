#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict
from typing import (
    Any,
    Collection,
    Iterator,
    Mapping,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
)

from .agent_based_api.v1 import register, Result, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, InventoryResult, StringTable
from .utils.interfaces import (
    CHECK_DEFAULT_PARAMETERS,
    check_multiple_interfaces,
    discover_interfaces,
    DISCOVERY_DEFAULT_PARAMETERS,
    Interface,
    mac_address_from_hexstring,
    render_mac_address,
    saveint,
)
from .utils.interfaces import Section as SectionInterfaces
from .utils.inventory_interfaces import Interface as InterfaceInv
from .utils.inventory_interfaces import inventorize_interfaces

Line = Sequence[str]
Lines = Iterator[Line]


def _canonize_name(name: str) -> str:
    return name.replace("_", " ").replace("  ", " ").rstrip()


def _line_to_mapping(
    headers: Line,
    line: Line,
) -> Mapping[str, str]:
    """
    >>> _line_to_mapping(["a", "b"], ["1", "2  ", "3"])
    {'a': '1', 'b': '2'}
    """
    return dict(
        zip(
            headers,
            (x.strip() for x in line),
        )
    )


class SectionCounters(NamedTuple):
    timestamp: Optional[float]
    interfaces: Mapping[str, Interface]
    found_windows_if: bool
    found_mk_dhcp_enabled: bool


def _parse_timestamp_and_instance_names(
    line: Line,
    lines: Lines,
) -> Tuple[Optional[float], Sequence[str]]:
    # The lines containing timestamp and nic names are consecutive:
    # [u'1418225545.73', u'510']
    # [u'8', u'instances:', 'NAME', ...]
    agent_timestamp = None
    try:
        # There may be other lines with same length but different
        # format. Thus we have to check if the current one is the
        # right one containing the agent timestamp.
        # In second place there's another integer which is a strong
        # hint for the 'agent timestamp'-line.
        agent_timestamp = float(line[0])
        int(line[1])
    except ValueError:
        pass

    try:
        line = next(lines)
    except StopIteration:
        instances: Sequence[str] = []
    else:
        instances = line[2:]
    return agent_timestamp, instances


def _parse_counters(
    raw_nic_names: Sequence[str],
    agent_section: Mapping[str, Line],
) -> Mapping[str, Interface]:
    interfaces: MutableMapping[str, Interface] = {}
    for idx, raw_nic_name in enumerate(raw_nic_names):
        name = _canonize_name(raw_nic_name)
        counters = {counter: int(line[idx]) for counter, line in agent_section.items()}
        interfaces.setdefault(
            name,
            Interface(
                index=str(idx + 1),
                descr=name,
                alias=name,
                type="loopback" in name.lower() and "24" or "6",
                speed=counters["10"],
                oper_status="1",
                in_octets=counters["-246"],
                in_ucast=counters["14"],
                in_bcast=counters["16"],
                in_discards=counters["18"],
                in_errors=counters["20"],
                out_octets=counters["-4"],
                out_ucast=counters["26"],
                out_bcast=counters["28"],
                out_discards=counters["30"],
                out_errors=counters["32"],
                out_qlen=counters["34"],
                oper_status_name="Connected",
            ),
        )
    return interfaces


def _filter_out_deprecated_plugin_lines(
    string_table: StringTable,
) -> Tuple[StringTable, bool, bool]:
    native_agent_data: StringTable = []
    found_windows_if = False
    found_mk_dhcp_enabled = False

    for line in (lines := iter(string_table)):

        # from mk_dhcp_enabled.bat
        if line[0].startswith("[dhcp_start]"):
            found_mk_dhcp_enabled = True
            for l in lines:
                if l[0].startswith("[dhcp_end]"):
                    break
            continue

        # from windows_if.ps1 or wmic_if.bat
        if line[0].startswith("[teaming_start]"):
            found_windows_if = True
            for l in lines:
                if l[0].startswith("[teaming_end]"):
                    break
            continue

        # from windows_if.ps1 or wmic_if.bat
        if {"Node", "MACAddress", "Name", "NetConnectionID", "NetConnectionStatus"}.issubset(line):
            found_windows_if = True
            for l in lines:
                if len(l) < 4:
                    native_agent_data.append(l)
                    break
            continue

        native_agent_data.append(line)

    return native_agent_data, found_windows_if, found_mk_dhcp_enabled


def parse_winperf_if(string_table: StringTable) -> SectionCounters:
    agent_timestamp = None
    raw_nic_names: Sequence[str] = []
    agent_section: MutableMapping[str, Line] = {}

    # There used to be only a single winperf_if-section which contained both the native agent data
    # and plugin data which is now located in the sections winperf_if_... For compatibily reasons,
    # we still handle this case by filtering out the plugin data and advising the user to update
    # the agent.
    (
        string_table_filtered,
        found_windows_if,
        found_mk_dhcp_enabled,
    ) = _filter_out_deprecated_plugin_lines(string_table)

    for line in (lines := iter(string_table_filtered)):  # pylint:disable=superfluous-parens
        if len(line) in (2, 3) and not line[-1].endswith("count"):
            # Do not consider lines containing counters:
            # ['-122', '38840302775', 'bulk_count']
            # ['10', '10000000000', 'large_rawcount']
            agent_timestamp, raw_nic_names = _parse_timestamp_and_instance_names(
                line,
                lines,
            )
        else:
            agent_section.setdefault(line[0], line[1:])

    return SectionCounters(
        timestamp=agent_timestamp,
        interfaces=_parse_counters(
            raw_nic_names,
            agent_section,
        ),
        found_windows_if=found_windows_if,
        found_mk_dhcp_enabled=found_mk_dhcp_enabled,
    )


register.agent_section(
    name="winperf_if",
    parse_function=parse_winperf_if,
    supersedes=["if", "if64"],
)


class TeamingData(NamedTuple):
    team_name: str
    name: str


SectionTeaming = Mapping[str, TeamingData]


def parse_winperf_if_teaming(string_table: StringTable) -> SectionTeaming:
    return {
        guid: TeamingData(
            team_name=line_dict["TeamName"],
            name=_canonize_name(name),
        )
        for line_dict in (
            _line_to_mapping(
                string_table[0],
                line,
            )
            for line in string_table[1:]
        )
        for guid, name in zip(
            line_dict["GUID"].split(";"),
            line_dict["MemberDescriptions"].split(";"),
        )
    }


register.agent_section(
    name="winperf_if_teaming",
    parse_function=parse_winperf_if_teaming,
)


class AdditionalIfData(NamedTuple):
    name: str
    alias: str
    speed: int
    oper_status: str
    oper_status_name: str
    mac_address: str
    guid: Optional[str]  # wmic_if.bat does not produce this


SectionExtended = Collection[AdditionalIfData]

# Windows NetConnectionStatus Table to ifOperStatus Table
# 1 up
# 2 down
# 3 testing
# 4 unknown
# 5 dormant
# 6 notPresent
# 7 lowerLayerDown
_NetConnectionStatus_TO_OPER_STATUS: Mapping[str, Tuple[str, str]] = {
    "0": ("2", "Disconnected"),
    "1": ("2", "Connecting"),
    "2": ("1", "Connected"),
    "3": ("2", "Disconnecting"),
    "4": ("2", "Hardware not present"),
    "5": ("2", "Hardware disabled"),
    "6": ("2", "Hardware malfunction"),
    "7": ("7", "Media disconnected"),
    "8": ("2", "Authenticating"),
    "9": ("2", "Authentication succeeded"),
    "10": ("2", "Authentication failed"),
    "11": ("2", "Invalid address"),
    "12": ("2", "Credentials required"),
}


def parse_winperf_if_win32_networkadapter(string_table: StringTable) -> SectionExtended:
    return [
        AdditionalIfData(
            name=_canonize_name(line_dict["Name"]),
            alias=line_dict["NetConnectionID"],
            # Some interfaces report several exabyte as bandwidth when down ...
            speed=speed
            if "Speed" in line_dict and (speed := saveint(line_dict["Speed"])) <= 1024**5
            else 0,
            oper_status=oper_status,
            oper_status_name=oper_status_name,
            mac_address=line_dict["MACAddress"],
            guid=line_dict.get("GUID"),
        )
        for line_dict in (
            _line_to_mapping(
                string_table[0],
                line,
            )
            for line in string_table[1:]
        )
        for oper_status, oper_status_name in [
            _NetConnectionStatus_TO_OPER_STATUS.get(
                line_dict["NetConnectionStatus"],
                ("2", "Disconnected"),
            )
        ]
        # we need to ignore data on interfaces in the optional
        # wmic section which are marked as non-existing, since
        # it may happen that there are non-existing interfaces
        # with the same nic_name as an active one (at least on HP
        # hardware)
        if line_dict["NetConnectionStatus"] != "4"
    ]


register.agent_section(
    name="winperf_if_win32_networkadapter",
    parse_function=parse_winperf_if_win32_networkadapter,
    parsed_section_name="winperf_if_extended",
)


def parse_winperf_if_get_netadapter(string_table: StringTable) -> SectionExtended:
    return [
        AdditionalIfData(
            name=_canonize_name(line[0]),
            alias=line[1],
            speed=int(speed_str) if (speed_str := line[2]) else 0,
            oper_status=line[3],
            oper_status_name=line[4],
            mac_address=line[5].replace("-", ":"),
            guid=line[6],
        )
        for line in string_table
    ]


register.agent_section(
    name="winperf_if_get_netadapter",
    parse_function=parse_winperf_if_get_netadapter,
    parsed_section_name="winperf_if_extended",
)

SectionDHPC = Collection[Mapping[str, str]]


def parse_winperf_if_dhcp(string_table: StringTable) -> SectionDHPC:
    # wmic is bugged on some windows versions such that we can't use proper csv output, only
    # visual tables. Those aren't properly split up by the check_mk parser.
    # Try to fix that mess
    return [
        _line_to_mapping(
            # assumption 1: the two header fields contain no spaces
            string_table[0],
            [
                # assumption 2: only the description contains spaces
                " ".join(line[:-1]),
                line[-1],
            ],
        )
        for line in string_table[1:]
    ]


register.agent_section(
    name="winperf_if_dhcp",
    parse_function=parse_winperf_if_dhcp,
)


def _normalize_name(
    name: str,
    names: Collection[str],
) -> str:
    """
    >>> _normalize_name("my interface #3", ["my interface 1", "my interface 2", "my interface 3"])
    'my interface 3'
    >>> _normalize_name("my interface(R)", ["my interface[R]", "another interface(?)"])
    'my interface(R)'
    """
    # Intel[R] PRO 1000 MT-Desktopadapter__3   (perf counter)
    # Intel(R) PRO/1000 MT-Desktopadapter 3    (wmic name)
    # Intel(R) PRO/1000 MT-Desktopadapter #3   (wmic InterfaceDescription)
    mod_name = name
    for from_token, to_token in [("/", " "), ("(", "["), (")", "]"), ("#", " ")]:
        for n in names:
            if from_token in n:
                # we do not modify it if this character is in any of the counter names
                break
        else:
            mod_name = mod_name.replace(from_token, to_token).replace("  ", " ")
    return mod_name


def _match_add_data_to_interfaces(
    interface_names: Collection[str],
    section_teaming: SectionTeaming,
    section_extended: SectionExtended,
):
    additional_data: MutableMapping[str, AdditionalIfData] = {}

    for add_data in section_extended:
        if add_data.guid is not None and (teaming_entry := section_teaming.get(add_data.guid)):
            name = teaming_entry.name
        else:
            name = add_data.name

        # Exact match
        if name in interface_names:
            additional_data.setdefault(name, add_data)
            continue

        # In the perf counters the nics have strange suffixes, e.g.
        # Ethernetadapter der AMD-PCNET-Familie 2 - Paketplaner-Miniport, while
        # in wmic it's only named "Ethernetadapter der AMD-PCNET-Familie 2".
        if (
            mod_name := _normalize_name(
                name,
                interface_names,
            )
        ) in interface_names:
            additional_data.setdefault(mod_name, add_data)
            continue

        for name in interface_names:
            if name.startswith(mod_name + " "):
                l = len(mod_name)
                if not (name[l:].strip()[0]).isdigit():
                    additional_data.setdefault(name, add_data)
                    break

    return additional_data


def _merge_sections(
    interfaces: Mapping[str, Interface],
    section_teaming: Optional[SectionTeaming],
    section_extended: Optional[SectionExtended],
) -> SectionInterfaces:

    section_teaming = section_teaming or {}
    additional_data = (
        _match_add_data_to_interfaces(
            interfaces,
            section_teaming,
            section_extended,
        )
        if section_extended
        else {}
    )

    return [
        Interface(
            **{
                **asdict(interface),
                **dict(
                    alias=add_if_data.alias,
                    speed=add_if_data.speed or interface.speed,
                    group=section_teaming[add_if_data.guid].team_name
                    if add_if_data.guid in section_teaming
                    else None,
                    oper_status=add_if_data.oper_status,
                    oper_status_name=add_if_data.oper_status_name,
                    phys_address=mac_address_from_hexstring(add_if_data.mac_address),
                ),
            }
        )
        if (add_if_data := additional_data.get(name))
        else interface
        for name, interface in interfaces.items()
    ]


def discover_winperf_if(
    params: Sequence[Mapping[str, Any]],
    section_winperf_if: Optional[SectionCounters],
    section_winperf_if_teaming: Optional[SectionTeaming],
    section_winperf_if_extended: Optional[SectionExtended],
    section_winperf_if_dhcp: Optional[SectionDHPC],
) -> DiscoveryResult:
    if not section_winperf_if:
        return
    yield from discover_interfaces(
        params,
        _merge_sections(
            section_winperf_if.interfaces,
            section_winperf_if_teaming,
            section_winperf_if_extended,
        ),
    )


def check_winperf_if(
    item: str,
    params: Mapping[str, Any],
    section_winperf_if: Optional[SectionCounters],
    section_winperf_if_teaming: Optional[SectionTeaming],
    section_winperf_if_extended: Optional[SectionExtended],
    section_winperf_if_dhcp: Optional[SectionDHPC],
) -> CheckResult:
    if not section_winperf_if:
        return

    yield from check_multiple_interfaces(
        item,
        params,
        _merge_sections(
            section_winperf_if.interfaces,
            section_winperf_if_teaming,
            section_winperf_if_extended,
        ),
        group_name="Teaming",
        timestamp=section_winperf_if.timestamp,
    )
    if section_winperf_if_dhcp and (
        dhcp_res := _check_dhcp(
            item,
            section_winperf_if.interfaces,
            section_winperf_if_dhcp,
        )
    ):
        yield dhcp_res
    yield from _check_deprecated_plugins(
        section_winperf_if.found_windows_if,
        section_winperf_if.found_mk_dhcp_enabled,
    )


def _check_dhcp(
    item: str,
    interface_names: Collection[str],
    section_dhcp: SectionDHPC,
) -> Optional[Result]:
    for dhcp_data in section_dhcp:
        try:
            match = int(dhcp_data["index"]) == int(item)
        except (KeyError, ValueError):
            match = (
                _normalize_name(
                    dhcp_data["Description"],
                    interface_names,
                )
                == item
            )

        if not match:
            continue

        if dhcp_data["DHCPEnabled"] == "TRUE":
            return Result(
                state=State.WARN,
                summary="DHCP: enabled",
            )
        return Result(
            state=State.OK,
            summary="DHCP: disabled",
        )
    return None


def _check_deprecated_plugins(
    windows_if: bool,
    mk_dhcp_enabled: bool,
) -> CheckResult:
    if windows_if:
        yield Result(
            state=State.CRIT,
            summary="Detected deprecated version of plugin 'windows_if.ps1' or 'wmic_if.bat' "
            "(bakery ruleset 'Network interfaces on Windows'). Please update the agent plugin.",
        )
    if mk_dhcp_enabled:
        yield Result(
            state=State.CRIT,
            summary="Detected deprecated version of plugin 'mk_dhcp_enabled.bat'. Please update "
            "the agent plugin.",
        )


register.check_plugin(
    name="winperf_if",
    sections=[
        "winperf_if",
        "winperf_if_teaming",
        "winperf_if_extended",
        "winperf_if_dhcp",
    ],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_winperf_if,
    check_ruleset_name="if",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_winperf_if,
)


def inventory_winperf_if(
    section_winperf_if: Optional[SectionCounters],
    section_winperf_if_teaming: Optional[SectionTeaming],
    section_winperf_if_extended: Optional[SectionExtended],
) -> InventoryResult:
    if not section_winperf_if:
        return
    interfaces = _merge_sections(
        section_winperf_if.interfaces,
        section_winperf_if_teaming,
        section_winperf_if_extended,
    )
    yield from inventorize_interfaces(
        {
            "usage_port_types": [
                "6",
                "32",
                "62",
                "117",
                "127",
                "128",
                "129",
                "180",
                "181",
                "182",
                "205",
                "229",
            ],
        },
        (
            InterfaceInv(
                index=interface.index[-1],
                descr=interface.descr,
                alias=interface.alias,
                type=interface.type,
                speed=int(interface.speed),
                oper_status=int(interface.oper_status[0]),
                phys_address=render_mac_address(interface.phys_address),
            )
            for interface in sorted(
                interfaces,
                key=lambda iface: int(iface.index[-1]),
            )
            # Useless entries for "TenGigabitEthernet2/1/21--Uncontrolled"
            # Ignore useless half-empty tables (e.g. Viprinet-Router)
            if interface.type not in ("231", "232") and interface.speed
        ),
        len(interfaces),
    )


# TODO: make this plugin use the inventory ruleset inv_if
register.inventory_plugin(
    name="winperf_if",
    sections=[
        "winperf_if",
        "winperf_if_teaming",
        "winperf_if_extended",
    ],
    inventory_function=inventory_winperf_if,
)
