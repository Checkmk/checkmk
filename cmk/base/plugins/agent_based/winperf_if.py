#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import (
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from .agent_based_api.v1 import (
    register,
    Result,
    State as state,
    type_defs,
)
from .utils import interfaces

# Example output from agent
# <<<winperf_if>>>
# 1366721523.71 510
# 3 instances: Ethernetadapter_der_AMD-PCNET-Familie__2_-_Paketplaner-Miniport Ethernetadapter_der_AMD-PCNET-Familie_-_Paketplaner-Miniport MS_TCP_Loopback_interface
# -122 43364 1085829 41602 bulk_count
# -110 293 4174 932 counter
# -244 138 3560 466 counter
# -58 155 614 466 counter
# 10 100000000 100000000 10000000 rawcount
# -246 21219 780491 20801 counter
# 14 0 383 466 counter
# 16 138 3176 0 counter
# 18 0 0 0 rawcount
# 20 0 0 0 rawcount
# 22 0 1 0 rawcount
# -4 22145 305338 20801 counter
# 26 0 428 466 counter
# 28 155 186 0 counter
# 30 0 0 0 rawcount
# 32 0 0 0 rawcount
# 34 0 0 0 rawcount
# <<<winperf_if:sep(44)>>>
# Node,MACAddress,Name,NetConnectionID,NetConnectionStatus
# WINDOWSXP,08:00:27:8D:47:A4,Ethernetadapter der AMD-PCNET-Familie,LAN-Verbindung,2
# WINDOWSXP,,Asynchroner RAS-Adapter,,
# WINDOWSXP,08:00:27:8D:47:A4,Paketplaner-Miniport,,
# WINDOWSXP,,WAN-Miniport (L2TP),,
# WINDOWSXP,50:50:54:50:30:30,WAN-Miniport (PPTP),,
# WINDOWSXP,33:50:6F:45:30:30,WAN-Miniport (PPPOE),,
# WINDOWSXP,,Parallelanschluss (direkt),,
# WINDOWSXP,,WAN-Miniport (IP),,
# WINDOWSXP,00:E5:20:52:41:53,Paketplaner-Miniport,,
# WINDOWSXP,08:00:27:35:20:4D,Ethernetadapter der AMD-PCNET-Familie,LAN-Verbindung 2,2
# WINDOWSXP,08:00:27:35:20:4D,Paketplaner-Miniport,,
#
# ------- DHCP-section -------
# This section had a live time of two months (26.10. - 11.12.2015) and was replaced by
# '<<<winperf_if>>>'
# [dhcp_start]
# ...
# [dhcp_end]
#
# Example output for the optional dhcp section. If this plugin is active, any interface for which
# dhcp is enabled will warn
# <<<dhcp:sep(44)>>>
# Node,Description,DHCPEnabled
# WINDOWS,Intel(R) PRO/1000 MT-Desktopadapter,TRUE
# WINDOWS,WAN Miniport (IP),FALSE
# WINDOWS,Microsoft-ISATAP-Adapter,FALSE
# WINDOWS,RAS Async Adapter,FALSE
# WINDOWS,Intel(R) PRO/1000 MT-Desktopadapter #2,TRUE

Line = Sequence[str]
Lines = Iterator[Line]
NICNames = Sequence[str]
ParsedSubSectionLine = Mapping[str, str]
RawSubSection = List[ParsedSubSectionLine]
SubSection = Dict[str, ParsedSubSectionLine]
AgentTimestamp = Optional[float]
AgentSection = Dict[str, Line]
Section = Tuple[AgentTimestamp, interfaces.Section, SubSection]


@dataclasses.dataclass
class NICAttr:
    index: int
    counters: Dict[str, Union[str, int]]


NICAttrs = Dict[str, NICAttr]


def winperf_if_canonize_nic_name(name: str) -> str:
    return name.replace("_", " ").replace("  ", " ").rstrip()


def winperf_if_normalize_nic_name(
    name: str,
    nic_names: NICNames,
) -> str:
    # Intel[R] PRO 1000 MT-Desktopadapter__3   (perf counter)
    # Intel(R) PRO/1000 MT-Desktopadapter 3    (wmic name)
    # Intel(R) PRO/1000 MT-Desktopadapter #3   (wmic InterfaceDescription)
    mod_nic_name = name
    for from_token, to_token in [("/", " "), ("(", "["), (")", "]"), ("#", " ")]:
        for n in nic_names:
            if from_token in n:
                # we do not modify it if this character is in any of the counter names
                break
        else:
            mod_nic_name = mod_nic_name.replace(from_token, to_token).replace("  ", " ")
    return mod_nic_name


def _parse_winperf_if_sub_section(
    lines: Lines,
    terminating_key: str,
    headers: Line,
) -> RawSubSection:
    section = []
    for line in lines:
        if line[0] == terminating_key:
            break

        if terminating_key == '[teaming_end]':
            section.append(_parse_winperf_if_teaming_section_line(line, headers))
        elif terminating_key == '[dhcp_end]':
            section.append(_parse_winperf_if_dhcp_section_line(line, headers))
    return section


def _parse_winperf_if_dhcp_section_line(
    line: Line,
    headers: Line,
) -> ParsedSubSectionLine:
    # wmic is bugged on some windows versions such that we can't use proper csv output, only
    # visual tables. Those aren't properly split up by the check_mk parser.
    # Try to fix that mess

    # assumption 1: header fields contain no spaces
    num_fields = len(headers)

    # assumption 2: only the leftmost field contains spaces
    lm_field = " ".join(line[:(num_fields - 1) * -1])
    line = [lm_field] + list(line[(len(line) - num_fields + 1):])
    return dict(zip(headers, [x.rstrip() for x in line]))


def _parse_winperf_if_teaming_section_line(
    line: Line,
    headers: Line,
) -> ParsedSubSectionLine:
    return dict(zip(headers, [x.rstrip() for x in line]))


def _parse_winperf_if_agent_section_timestamp_and_instance_names(
    line: Line,
    lines: Lines,
) -> Tuple[AgentTimestamp, NICNames]:
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
        instances: NICNames = []
    else:
        instances = line[2:]
    return agent_timestamp, instances


def _parse_winperf_if_section(
    string_table: type_defs.AgentStringTable
) -> Tuple[AgentTimestamp, NICNames, AgentSection, RawSubSection, RawSubSection, RawSubSection]:
    agent_timestamp = None
    raw_nic_names: NICNames = []
    agent_section: AgentSection = {}
    plugin_section: RawSubSection = []
    dhcp_section = []
    teaming_section = []

    plugin_section_header = None
    lines = iter(string_table)
    for line in lines:
        if line[0] == "[dhcp_start]":
            dhcp_section_headers = next(lines)
            dhcp_section.extend(
                _parse_winperf_if_sub_section(lines, '[dhcp_end]', dhcp_section_headers))
            continue

        if line[0].startswith("[teaming_start]"):
            teaming_section_headers = next(lines)
            teaming_section.extend(
                _parse_winperf_if_sub_section(lines, '[teaming_end]', teaming_section_headers))
            continue

        if {'Node', 'MACAddress', 'Name', 'NetConnectionID', 'NetConnectionStatus'}.issubset(line):
            plugin_section_header = line
            continue

        if len(line) in (2, 3) and not line[-1].endswith("count"):
            # Do not consider lines containing counters:
            # ['-122', '38840302775', 'bulk_count']
            # ['10', '10000000000', 'large_rawcount']
            agent_timestamp, raw_nic_names = _parse_winperf_if_agent_section_timestamp_and_instance_names(
                line, lines)
            plugin_section_header = None
            continue

        if plugin_section_header:
            plugin_section.append(dict(zip(plugin_section_header, [x.strip() for x in line])))

        else:  # agent section
            agent_section.setdefault(line[0], line[1:])

    return agent_timestamp, raw_nic_names, agent_section, plugin_section, dhcp_section, teaming_section


def _prepare_winperf_if_dhcp_section(
    nic_names: NICNames,
    dhcp_section: RawSubSection,
) -> SubSection:
    dhcp_info: SubSection = {}
    for row in dhcp_section:
        nic_name = winperf_if_normalize_nic_name(row["Description"], nic_names)
        dhcp_info.setdefault(nic_name, row)
    return dhcp_info


def _prepare_winperf_if_teaming_section(teaming_section: RawSubSection) -> SubSection:
    return {
        guid: {k: v.strip() for k, v in dict_entry.items()} for dict_entry in teaming_section
        for guid in dict_entry.get('GUID', '').split(';')
    }


def _prepare_winperf_if_plugin_section(
    nic_names: NICNames,
    plugin_section: RawSubSection,
    teaming_info: SubSection,
) -> SubSection:
    plugin_info: SubSection = {}
    for row in plugin_section:
        # we need to ignore data on interfaces in the optional
        # wmic section which are marked as non-existing, since
        # it may happen that there are non-existing interfaces
        # with the same nic_name as an active one (at least on HP
        # hardware)
        if row.get("NetConnectionStatus") == "4":
            continue

        guid = row.get("GUID")
        if guid in teaming_info:
            guid_entry = teaming_info[guid]
            guid_to_name = dict(
                zip(guid_entry["GUID"].split(";"), guid_entry["MemberDescriptions"].split(";")))
            nic_name = winperf_if_canonize_nic_name(guid_to_name[guid])

        elif "Name" in row:
            nic_name = winperf_if_canonize_nic_name(row["Name"])

        else:
            continue

        # Exact match
        if nic_name in nic_names:
            plugin_info.setdefault(nic_name, row)
            continue

        # In the perf counters the nics have strange suffixes, e.g.
        # Ethernetadapter der AMD-PCNET-Familie 2 - Paketplaner-Miniport, while
        # in wmic it's only named "Ethernetadapter der AMD-PCNET-Familie 2".
        mod_nic_name = winperf_if_normalize_nic_name(nic_name, nic_names)
        if mod_nic_name in nic_names:
            plugin_info.setdefault(mod_nic_name, row)
            continue

        for name in nic_names:
            if name.startswith(mod_nic_name + " "):
                l = len(mod_nic_name)
                if not (name[l:].strip()[0]).isdigit():
                    plugin_info.setdefault(name, row)
                    break
    return plugin_info


# Windows NetConnectionStatus Table to ifOperStatus Table
# 1 up
# 2 down
# 3 testing
# 4 unknown
# 5 dormant
# 6 notPresent
# 7 lowerLayerDown
_CONNECTION_STATES = {
    '0': ('2', 'Disconnected'),
    '1': ('2', 'Connecting'),
    '2': ('1', 'Connected'),
    '3': ('2', 'Disconnecting'),
    '4': ('2', 'Hardware not present'),
    '5': ('2', 'Hardware disabled'),
    '6': ('2', 'Hardware malfunction'),
    '7': ('7', 'Media disconnected'),
    '8': ('2', 'Authenticating'),
    '9': ('2', 'Authentication succeeded'),
    '10': ('2', 'Authentication failed'),
    '11': ('2', 'Invalid address'),
    '12': ('2', 'Credentials required'),
}


def _get_if_table(
    nic_attrs: NICAttrs,
    plugin_info: SubSection,
    teaming_info: SubSection,
) -> interfaces.Section:
    # Now convert the dicts into the format that is needed by if.include
    if_table = []
    for nic_name, nic_attr in nic_attrs.items():
        nic = nic_attr.counters
        nic.setdefault('index', nic_attr.index)
        nic.update(plugin_info.get(nic_name, {}))

        bandwidth = interfaces.saveint(nic.get('Speed'))
        # Some interfaces report several exabyte as bandwidth when down..
        if bandwidth > 1024**5:
            # Greater than petabyte
            bandwidth = 0

        # Automatically group teamed interfaces
        guid = nic.get("GUID")
        group = teaming_info.get(guid, {}).get("TeamName") if isinstance(guid, str) else None

        # if we have no status, but link information, we assume IF is connected
        connection_status = nic.get('NetConnectionStatus')
        if not connection_status:
            connection_status = '2'

        oper_status, oper_status_name = _CONNECTION_STATES[str(connection_status)]

        if_table.append(
            interfaces.Interface(
                index=str(nic['index']),
                descr=nic_name,
                alias=str(nic.get('NetConnectionID', nic_name)),
                type="loopback" in nic_name.lower() and '24' or '6',
                speed=bandwidth or interfaces.saveint(nic['10']),
                oper_status=oper_status,
                in_octets=interfaces.saveint(nic['-246']),
                in_ucast=interfaces.saveint(nic['14']),
                in_bcast=interfaces.saveint(nic['16']),
                in_discards=interfaces.saveint(nic['18']),
                in_errors=interfaces.saveint(nic['20']),
                out_octets=interfaces.saveint(nic['-4']),
                out_ucast=interfaces.saveint(nic['26']),
                out_bcast=interfaces.saveint(nic['28']),
                out_discards=interfaces.saveint(nic['30']),
                out_errors=interfaces.saveint(nic['32']),
                out_qlen=interfaces.saveint(nic['34']),
                phys_address=interfaces.mac_address_from_hexstring(str(nic.get('MACAddress', ''))),
                oper_status_name=oper_status_name,
                group=group,
            ))

    return if_table


def _parse_winperf_if_nic_attrs(
    raw_nic_names: NICNames,
    agent_section: AgentSection,
) -> NICAttrs:
    nic_attrs: NICAttrs = {}
    for idx, raw_nic_name in enumerate(raw_nic_names):
        nic_name = winperf_if_canonize_nic_name(raw_nic_name)
        nic_attrs.setdefault(
            nic_name,
            NICAttr(idx + 1, {counter: int(line[idx]) for counter, line in agent_section.items()}))
    return nic_attrs


def parse_winperf_if(string_table: type_defs.AgentStringTable) -> Section:
    (agent_timestamp, raw_nic_names, agent_section, plugin_section, dhcp_section,
     teaming_section) = _parse_winperf_if_section(string_table)

    # Based on the raw nic names we structure the interface table
    nic_attrs = _parse_winperf_if_nic_attrs(raw_nic_names, agent_section)
    nic_names = list(nic_attrs)

    teaming_info = _prepare_winperf_if_teaming_section(teaming_section)
    plugin_info = _prepare_winperf_if_plugin_section(nic_names, plugin_section, teaming_info)

    if_table = _get_if_table(nic_attrs, plugin_info, teaming_info)
    dhcp_info = _prepare_winperf_if_dhcp_section(nic_names, dhcp_section)
    return agent_timestamp, if_table, dhcp_info


register.agent_section(
    name='winperf_if',
    parse_function=parse_winperf_if,
)


def discover_winperf_if(
    params: Sequence[type_defs.Parameters],
    section: Section,
) -> type_defs.DiscoveryResult:
    yield from interfaces.discover_interfaces(
        params,
        section[1],
    )


def check_winperf_if(
    item: str,
    params: type_defs.Parameters,
    section: Section,
) -> type_defs.CheckResult:
    agent_timestamp, if_table, dhcp_info = section
    yield from interfaces.check_multiple_interfaces(
        item,
        params,
        if_table,
        group_name="Teaming",
        timestamp=agent_timestamp,
    )

    dhcp_result = check_if_dhcp(item, dhcp_info)
    if dhcp_result:
        yield dhcp_result


def check_if_dhcp(
    item: str,
    dhcp_info: SubSection,
) -> Optional[Result]:
    for nic_name, attrs in dhcp_info.items():
        try:
            match = int(attrs['index']) == int(item)
        except (KeyError, ValueError):
            match = nic_name == item

        if not match:
            continue

        dhcp_enabled = attrs["DHCPEnabled"]
        if dhcp_enabled == "TRUE":
            return Result(
                state=state.WARN,
                summary="DHCP: enabled",
            )
        return Result(
            state=state.OK,
            summary="DHCP: %s" % dhcp_enabled,
        )
    return None


register.check_plugin(
    name="winperf_if",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type="all",
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_winperf_if,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_winperf_if,
)
