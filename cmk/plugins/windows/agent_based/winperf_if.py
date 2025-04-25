#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO(sk): Code below is utter bs and must be fully rewritten
# Lack of comments with links to MSDN. THIS IS MUST HAVE FOR WINDOWS.
# Tripled code for the same thing. This is a bad idea.
# Lack of typing
# Absolutely inappropriate list comprehension counting 40+ lines of code
# Wrong naming oper_status has no "media disconnect" status
# Bad typing dict[str,tuple[str,str]]  - is not typing at all

from collections.abc import Callable, Collection, Iterator, Mapping, MutableMapping, Sequence
from dataclasses import asdict
from functools import partial
from typing import Any, Final, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    InventoryPlugin,
    InventoryResult,
    Result,
    RuleSetType,
    State,
    StringTable,
)
from cmk.plugins.lib import interfaces
from cmk.plugins.lib.inventory_interfaces import Interface as InterfaceInv
from cmk.plugins.lib.inventory_interfaces import inventorize_interfaces

Line = Sequence[str]
Lines = Iterator[Line]


# Pseudo counters must be in sync with code in windows agent, grep if_status_pseudo_counter in WA
_IF_STATUS_PSEUDO_COUNTER: Final[str] = "2002"
_IF_MAC_PSEUDO_COUNTER: Final[str] = "2006"


def _canonize_name(name: str) -> str:
    return " ".join(name.replace("_", " ").split())


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
    timestamp: float | None
    interfaces: Mapping[str, interfaces.InterfaceWithCounters]
    found_windows_if: bool
    found_mk_dhcp_enabled: bool


def _parse_timestamp_and_instance_names(
    line: Line,
    lines: Lines,
) -> tuple[float | None, Sequence[str]]:
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


def _get_windows_if_status(counter_index: int) -> str:
    return interfaces.get_if_state_name(str(counter_index))


def _get_oper_status(agent_section: Mapping[str, Line], idx: int) -> int:
    """returns oper status, see MSDN meaning, from pseudo counter if presented
    otherwise 1 (up)"""
    if line := agent_section.get(_IF_STATUS_PSEUDO_COUNTER):
        return int(line[idx])
    return 1


def _get_mac(agent_section: Mapping[str, Line], idx: int) -> str:
    """returns mac address byte string if pseudo counter exists
    otherwise empty"""
    if line := agent_section.get(_IF_MAC_PSEUDO_COUNTER):
        mac = interfaces.mac_address_from_hexstring(line[idx])
        # WA can return 0 if MAC is not known/on error, defense is implemented on base of beta
        # testing where minimal errors in WA output led to a crash in WATO
        return "" if mac == "\0x00" else mac
    return ""


def _parse_counters(
    raw_nic_names: Sequence[str],
    agent_section: Mapping[str, Line],
) -> Mapping[str, interfaces.InterfaceWithCounters]:
    def get_int_value(pos: int, row: str) -> int:
        return int(agent_section[row][pos])

    ifaces: dict[str, interfaces.InterfaceWithCounters] = {}
    for idx, raw_nic_name in enumerate(raw_nic_names):
        counter: Callable[[str], int] = partial(get_int_value, idx)
        name = _canonize_name(raw_nic_name)
        oper_status = _get_oper_status(agent_section, idx)
        ifaces.setdefault(
            name,
            interfaces.InterfaceWithCounters(
                interfaces.Attributes(
                    index=str(idx + 1),
                    descr=name,
                    alias=name,
                    type="loopback" in name.lower() and "24" or "6",
                    speed=counter("10"),
                    oper_status=str(oper_status),
                    out_qlen=counter("34"),
                    oper_status_name=_get_windows_if_status(oper_status),
                    phys_address=_get_mac(agent_section, idx),
                ),
                interfaces.Counters(
                    in_octets=counter("-246"),
                    in_ucast=counter("14"),
                    in_nucast=counter("16"),
                    in_disc=counter("18"),
                    in_err=counter("20"),
                    out_octets=counter("-4"),
                    out_ucast=counter("26"),
                    out_nucast=counter("28"),
                    out_disc=counter("30"),
                    out_err=counter("32"),
                ),
            ),
        )
    return ifaces


def _filter_out_deprecated_plugin_lines(
    string_table: StringTable,
) -> tuple[StringTable, bool, bool]:
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


def _is_first_line(line: Sequence[str]) -> bool:
    """
    Return true if the line[0] is a float, meaning timestamp.

    All other variants are assumed as malformed input.
    """
    # counter can.t contain dot in the name
    return "." in line[0]


def parse_winperf_if(string_table: StringTable) -> SectionCounters:
    # There used to be only a single winperf_if-section which contained both the native agent data
    # and plug-in data which is now located in the sections winperf_if_... For compatibily reasons,
    # we still handle this case by filtering out the plug-in data and advising the user to update
    # the agent.
    (
        string_table_filtered,
        found_windows_if,
        found_mk_dhcp_enabled,
    ) = _filter_out_deprecated_plugin_lines(string_table)

    agent_timestamp = None
    raw_nic_names: Sequence[str] = []
    agent_section: dict[str, Line] = {}

    for line in (lines := iter(string_table_filtered)):
        if _is_first_line(line):
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


agent_section_winperf_if = AgentSection(
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


agent_section_winperf_if_teaming = AgentSection(
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
    guid: str | None  # wmic_if.bat does not produce this


SectionExtended = Collection[AdditionalIfData]

# TODO(sk): remove this after deprecation of the corresponding plug-in winperf_if.ps1
# NOTE: this case os for command `Get-CimInstance -ClassName Win32_NetworkAdapter`
# Windows NetConnectionStatus Table to ifOperStatus Table
# 1 up
# 2 down
# 3 testing
# 4 unknown
# 5 dormant
# 6 notPresent
# 7 lowerLayerDown
_NetConnectionStatus_TO_OPER_STATUS: Mapping[str, tuple[str, str]] = {
    "0": ("2", "Disconnected"),
    "1": ("2", "Connecting"),
    "2": ("1", "up"),
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
            speed=(
                speed
                if "Speed" in line_dict
                and (speed := interfaces.saveint(line_dict["Speed"])) <= 1024**5
                else 0
            ),
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
                ("2", "down"),
            )
        ]
        # we need to ignore data on interfaces in the optional
        # wmic section which are marked as non-existing, since
        # it may happen that there are non-existing interfaces
        # with the same nic_name as an active one (at least on HP
        # hardware)
        if line_dict["NetConnectionStatus"] != "4"
    ]


agent_section_winperf_if_win32_networkadapter = AgentSection(
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


agent_section_winperf_if_get_netadapter = AgentSection(
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


agent_section_winperf_if_dhcp = AgentSection(
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
) -> Mapping[str, AdditionalIfData]:
    additional_data: dict[str, AdditionalIfData] = {}

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
    ifaces: Mapping[str, interfaces.InterfaceWithCounters],
    section_teaming: SectionTeaming | None,
    section_extended: SectionExtended | None,
) -> Sequence[interfaces.InterfaceWithCounters]:
    section_teaming = section_teaming or {}
    additional_data = (
        _match_add_data_to_interfaces(
            ifaces,
            section_teaming,
            section_extended,
        )
        if section_extended
        else {}
    )

    return [
        (
            interfaces.InterfaceWithCounters(
                attributes=interfaces.Attributes(
                    **{
                        **asdict(interface.attributes),
                        **{
                            "alias": add_if_data.alias,
                            "speed": add_if_data.speed or interface.attributes.speed,
                            "group": (
                                section_teaming[add_if_data.guid].team_name
                                if add_if_data.guid is not None
                                and add_if_data.guid in section_teaming
                                else None
                            ),
                            "oper_status": add_if_data.oper_status,
                            "oper_status_name": add_if_data.oper_status_name,
                            "phys_address": interfaces.mac_address_from_hexstring(
                                add_if_data.mac_address
                            ),
                        },
                    },
                ),
                counters=interface.counters,
            )
            if (add_if_data := additional_data.get(name))
            else interface
        )
        for name, interface in ifaces.items()
    ]


def discover_winperf_if(
    params: Sequence[Mapping[str, Any]],
    section_winperf_if: SectionCounters | None,
    section_winperf_if_teaming: SectionTeaming | None,
    section_winperf_if_extended: SectionExtended | None,
    section_winperf_if_dhcp: SectionDHPC | None,
) -> DiscoveryResult:
    if not section_winperf_if:
        return
    yield from interfaces.discover_interfaces(
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
    section_winperf_if: SectionCounters | None,
    section_winperf_if_teaming: SectionTeaming | None,
    section_winperf_if_extended: SectionExtended | None,
    section_winperf_if_dhcp: SectionDHPC | None,
) -> CheckResult:
    yield from _check_winperf_if(
        item,
        params,
        section_winperf_if,
        section_winperf_if_teaming,
        section_winperf_if_extended,
        section_winperf_if_dhcp,
        get_value_store(),
    )


def _check_winperf_if(
    item: str,
    params: Mapping[str, Any],
    section_winperf_if: SectionCounters | None,
    section_winperf_if_teaming: SectionTeaming | None,
    section_winperf_if_extended: SectionExtended | None,
    section_winperf_if_dhcp: SectionDHPC | None,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if not section_winperf_if:
        return

    ifaces = _merge_sections(
        section_winperf_if.interfaces,
        section_winperf_if_teaming,
        section_winperf_if_extended,
    )
    timestamps = (
        [section_winperf_if.timestamp] * len(ifaces)
        if section_winperf_if.timestamp is not None
        else None
    )
    yield from interfaces.check_multiple_interfaces(
        item,
        params,
        ifaces,
        group_name="Teaming",
        timestamps=timestamps,
        value_store=value_store,
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
) -> Result | None:
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
            summary="Detected deprecated version of plug-in 'windows_if.ps1' or 'wmic_if.bat' "
            "(bakery ruleset 'Network interfaces on Windows'). Please update the agent plug-in.",
        )
    if mk_dhcp_enabled:
        yield Result(
            state=State.CRIT,
            summary="Detected deprecated version of plug-in 'mk_dhcp_enabled.bat'. Please update "
            "the agent plug-in.",
        )


check_plugin_winperf_if = CheckPlugin(
    name="winperf_if",
    sections=[
        "winperf_if",
        "winperf_if_teaming",
        "winperf_if_extended",
        "winperf_if_dhcp",
    ],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_winperf_if,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_winperf_if,
)


def inventory_winperf_if(
    section_winperf_if: SectionCounters | None,
    section_winperf_if_teaming: SectionTeaming | None,
    section_winperf_if_extended: SectionExtended | None,
) -> InventoryResult:
    if not section_winperf_if:
        return
    ifaces = _merge_sections(
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
                index=interface.attributes.index[-1],
                descr=interface.attributes.descr,
                alias=interface.attributes.alias,
                type=interface.attributes.type,
                speed=int(interface.attributes.speed),
                oper_status=int(interface.attributes.oper_status[0]),
                phys_address=interfaces.render_mac_address(interface.attributes.phys_address),
            )
            for interface in sorted(
                ifaces,
                key=lambda iface: int(iface.attributes.index[-1]),
            )
            # Useless entries for "TenGigabitEthernet2/1/21--Uncontrolled"
            # Ignore useless half-empty tables (e.g. Viprinet-Router)
            if interface.attributes.type not in ("231", "232") and interface.attributes.speed
        ),
        len(ifaces),
    )


# TODO: make this plug-in use the inventory ruleset inv_if
inventory_plugin_winperf_if = InventoryPlugin(
    name="winperf_if",
    sections=[
        "winperf_if",
        "winperf_if_teaming",
        "winperf_if_extended",
    ],
    inventory_function=inventory_winperf_if,
)
