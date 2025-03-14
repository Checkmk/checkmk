#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This is how an Arista BGP SNMP message is constructed:
| ARISTA-BGP4V2-MIB::aristaBgp4V2Objects
|                            Peer<Item>
|                                     Connection-Type
|                                             IP
|                                                           Value
| [.1.3.6.1.4.1.30065.4.1.1].[2.1.11].[1.1].4.[192.168.4.5] "C0 A8 5C 00 "

e.g.:
| .1.3.6.1.4.1.30065.4.1.1.2.1.12.1.1.4.192.168.4.5 2
| => ARISTA-BGP4V2-MIB::aristaBgp4V2PeerAdminStatus.1.ipv4."192.168.4.5" =

Here is how those messages look like - removed leading 'ARISTA-BGP4V2-MIB::aristaBgp4V2Peer'
and translated IP addresses from hex to usual format
| ..LocalAddrType.1.ipv4."192.168.4.5" 1
| ..LocalAddr.1.ipv4."192.168.4.5" 192.168.4.4
| ..LocalPort.1.ipv4."192.168.4.5" 179
| ..LocalAs.1.ipv4."192.168.4.5" 65060
| ..LocalIdentifier.1.ipv4."192.168.4.5"  10.60.225.123
| ..RemotePort.1.ipv4."192.168.4.5" 37305
| ..RemoteAs.1.ipv4."192.168.4.5" 65000
| ..RemoteIdentifier.1.ipv4."192.168.4.5" 192.168.92.0
| ..AdminStatus.1.ipv4."192.168.4.5" 2
| ..State.1.ipv4."192.168.4.5" 6
| ..Description.1.ipv4."192.168.4.5" vxlan-sv4-san-ctl-1
| ..LastErrorCodeReceived.1.ipv4."192.168.4.5" 0
| ..LastErrorSubCodeReceived.1.ipv4."192.168.4.5" 0
| ..LastErrorReceivedTime.1.ipv4."192.168.4.5" 0
| ..LastErrorReceivedText.1.ipv4."192.168.4.5"
| ..LastErrorReceivedData.1.ipv4."192.168.4.5"
| ..LastErrorCodeSent.1.ipv4."192.168.4.5" 6
| ..LastErrorSubCodeSent.1.ipv4."192.168.4.5" 7
| ..LastErrorSentTime.1.ipv4."192.168.4.5" 0
| ..LastErrorSentText.1.ipv4."192.168.4.5"
| ..LastErrorSentData.1.ipv4."192.168.4.5"
| ..FsmEstablishedTime.1.ipv4."192.168.4.5" 1377443
| ..InUpdatesElapsedTime.1.ipv4."192.168.4.5" 1377443
| ..ConnectRetryInterval.1.ipv4."192.168.4.5" 4
| ..HoldTimeConfigured.1.ipv4."192.168.4.5" 180
| ..KeepAliveConfigured.1.ipv4."192.168.4.5" 60
| ..MinASOrigInterval.1.ipv4."192.168.4.5" 1
| ..MinRouteAdverInterval.1.ipv4."192.168.4.5" 1
| ..HoldTime.1.ipv4."192.168.4.5" 180
| ..KeepAlive.1.ipv4."192.168.4.5" 60
| ..InUpdates.1.ipv4."192.168.4.5" 6
| ..OutUpdates.1.ipv4."192.168.4.5" 6
| ..InTotalMessages.1.ipv4."192.168.4.5" 135114
| ..OutTotalMessages.1.ipv4."192.168.4.5" 135120
| ..FsmEstablishedTransitions.1.ipv4."192.168.4.5" 3

This is the data we can extract
| '192.168.92.1':
|  LocalAddrType:             'IPv4'
|  LocalAddr:                 '192.168.92.0'
|  LocalPort:                 '44759'
|  LocalAs:                   '65060'
|  LocalIdentifier:           '10.60.225.123'
|  RemotePort:                '179'
|  RemoteAs:                  '65060'
|  RemoteIdentifier:          '10.60.225.124'
|  AdminStatus:               'running'
|  State:                     'established'
|  Description:               'ibgp-def-vrf'
|  LastErrorCodeReceived:     '0'
|  LastErrorSubCodeReceived:  '0'
|  LastErrorReceivedTime:     '0'
|  LastErrorReceivedText:     'Cease/administrative reset'
|  LastErrorReceivedData:     ''
|  LastErrorCodeSent:         '0'
|  LastErrorSubCodeSent:      '0'
|  LastErrorSentTime:         '0'
|  LastErrorSentText:         ''
|  LastErrorSentData:         ''
|  FsmEstablishedTime:        '1896915'
|  InUpdatesElapsedTime:      '516836'
|  ConnectRetryInterval:      '4'
|  HoldTimeConfigured:        '180'
|  KeepAliveConfigured:       '60'
|  MinASOrigInterval:         '1'
|  MinRouteAdverInterval:     '1'
|  HoldTime:                  '180'
|  KeepAlive:                 '60'
|  InUpdates:                 '25'
|  OutUpdates:                '23'
|  InTotalMessages:           '143891'
|  OutTotalMessages:          '143888'
|  FsmEstablishedTransitions: '2'

"""

from collections.abc import Iterable, Mapping, Sequence
from typing import NamedTuple

from typing_extensions import TypedDict

from cmk.plugins.lib.ip_format import clean_v4_address, clean_v6_address

from .agent_based_api.v1 import (
    all_of,
    exists,
    Metric,
    OIDBytes,
    OIDEnd,
    register,
    render,
    Result,
    Service,
    ServiceLabel,
    SNMPTree,
    startswith,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringByteTable


class BGPData(NamedTuple):
    local_address: str
    local_identifier: str
    remote_as_number: int
    remote_identifier: str
    admin_state: str
    peer_state: str
    last_received_error: str
    established_time: int
    description: str
    bgp_version: int


Section = Mapping[str, BGPData]

AdminStateMapping = Mapping[str, int]
PeerStateMapping = Mapping[str, int]


class BGPPeerParams(TypedDict):
    admin_state_mapping: AdminStateMapping
    peer_state_mapping: PeerStateMapping


DEFAULT_ADMIN_STATE_MAPPING: AdminStateMapping = {
    "halted": 0,
    "running": 0,
}

DEFAULT_PEER_STATE_MAPPING: PeerStateMapping = {
    "idle": 0,
    "connect": 0,
    "active": 0,
    "opensent": 0,
    "openconfirm": 0,
    "established": 0,
}

DEFAULT_BGP_PEER_PARAMS = BGPPeerParams(
    admin_state_mapping=DEFAULT_ADMIN_STATE_MAPPING,
    peer_state_mapping=DEFAULT_PEER_STATE_MAPPING,
)


def _convert_address(value: str | list[int]) -> str:
    if not value:
        return "empty()"
    if isinstance(value, list):
        return clean_v4_address(value) if len(value) == 4 else clean_v6_address(value)
    split_value = value.split(".")
    return clean_v4_address(split_value) if len(split_value) == 4 else clean_v6_address(split_value)


def _create_item_data(entry: list[str | list[int]]) -> BGPData:
    return BGPData(
        local_address=_convert_address(entry[0]),
        local_identifier=_convert_address(entry[1]),
        remote_as_number=int(entry[2]) if isinstance(entry[2], str) else 0,
        remote_identifier=_convert_address(entry[3]),
        admin_state={
            "1": "halted",
            "2": "running",
        }.get(entry[4] if isinstance(entry[4], str) else "0", "unknown(%r)" % entry[4]),
        peer_state={
            "1": "idle",
            "2": "connect",
            "3": "active",
            "4": "opensent",
            "5": "openconfirm",
            "6": "established",
        }.get(entry[5] if isinstance(entry[5], str) else "0", "unknown(%r)" % entry[5]),
        last_received_error=entry[6] if isinstance(entry[6], str) else "unknown(%r)" % entry[6],
        established_time=int(entry[7]) if isinstance(entry[7], str) else 0,
        description=(
            (entry[-2] if isinstance(entry[-2], str) else "unknown(%r)" % entry[-2])
            if len(entry) > len(BGPData.__annotations__) - 1
            else "n/a"
        ),
        bgp_version=4,
    )


def _check_string_table(string_table: list[StringByteTable]) -> None:
    assert all(len(entry) >= len(BGPData.__annotations__) - 1 for entry in string_table[0]), (
        "Not all info elements have the size guessed from known names %d: %r"
        % (
            len(BGPData.__annotations__),
            [len(entry) for entry in string_table[0]],
        )
    )


def _clean_address(address_as_oids: Sequence[str]) -> str:
    addr_type = int(address_as_oids[0])
    addr_len = int(address_as_oids[1])
    addr_elements = address_as_oids[2 : 2 + addr_len]
    match addr_type:
        case 0:
            raise ValueError("Unknown address type is currently unsupported")
        case 1:
            return clean_v4_address(addr_elements)
        case 2:
            return clean_v6_address(addr_elements)
        case 3:
            return (
                f"{clean_v4_address(addr_elements[:-4])}%{_render_zone_index(addr_elements[-4:])}"
            )
        case 4:
            return (
                f"{clean_v6_address(addr_elements[:-4])}%{_render_zone_index(addr_elements[-4:])}"
            )
        case 16:
            raise ValueError("DNS domain names are currently unsupported")
        case _:
            raise ValueError(f"Unknown address type: {addr_type}")
    return clean_v4_address(addr_elements) if addr_type == 1 else clean_v6_address(addr_elements)


def _render_zone_index(elements: Iterable[str]) -> str:
    return ".".join(elements)


def parse_bgp_peer(string_table: list[StringByteTable]) -> Section:
    def remote_addr(oid_end: str) -> str:
        """Extracts data from OID_END (currently only RemoteAddr), format is:
        aristaBgp4V2PrefixGaugesEntry:
            aristaBgp4V2PeerInstance:        int - we don't need it now
            aristaBgp4V2PeerRemoteAddrType:  int - 1: IPv4, 2: IPv6.. see convert()
            aristaBgp4V2PeerRemoteAddr:      InetAddressType: int: len + IP-addr
            aristaBgp4V2PrefixGaugesAfi:     not provided in our case
            aristaBgp4V2PrefixGaugesSafi:    not provided in our case
        """
        oid_elements = oid_end.split(".")
        return _clean_address(oid_elements[1:])

    _check_string_table(string_table)
    return {remote_addr(str(entry[-1])): _create_item_data(entry) for entry in string_table[0]}


def parse_bgp_peer_cisco_2(string_table: list[StringByteTable]) -> Section:
    def remote_addr(oid_end: str) -> str:
        """Extracts data from OID_END (currently only RemoteAddr), format is:
        cbgpPeer2Entry:
            cbgpPeer2Type:       InetAddressType
            cbgpPeer2RemoteAddr: InetAddress
        """
        oid_elements = oid_end.split(".")
        return _clean_address(oid_elements)

    _check_string_table(string_table)
    return {remote_addr(str(entry[-1])): _create_item_data(entry) for entry in string_table[0]}


def parse_bgp_peer_cisco_3(string_table: list[StringByteTable]) -> Section:
    def remote_addr(oid_end: str) -> str:
        """Extracts data from OID_END (currently only RemoteAddr), format is:
        cbgpPeer3Entry:
            cbgpPeer3VrfId:      Unsigned32
            cbgpPeer3Type:       InetAddressType
            cbgpPeer3RemoteAddr: InetAddress
        """
        oid_elements = oid_end.split(".")
        return _clean_address(oid_elements[1:])

    _check_string_table(string_table)
    return {remote_addr(str(entry[-1])): _create_item_data(entry) for entry in string_table[0]}


def discover_bgp_peer(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item, labels=[ServiceLabel("cmk/bgp/description", peer.description)])
        for item, peer in section.items()
    )


def check_bgp_peer(
    item: str,
    params: BGPPeerParams,
    section: Section,
) -> CheckResult:
    if not (peer := section.get(item)):
        return
    yield Result(state=State.OK, summary=f"Description: {peer.description!r}")
    yield Result(state=State.OK, summary=f"Local address: {peer.local_address!r}")
    yield Result(
        state=State(
            params.get("admin_state_mapping", DEFAULT_ADMIN_STATE_MAPPING).get(peer.admin_state, 3)
        ),
        summary=f"Admin state: {peer.admin_state!r}",
    )
    yield Result(
        state=State(
            params.get("peer_state_mapping", DEFAULT_PEER_STATE_MAPPING).get(peer.peer_state, 3)
        ),
        summary=f"Peer state: {peer.peer_state!r}",
    )
    yield Result(
        state=State.OK,
        summary=f"Established time: {render.timespan(peer.established_time)}",
    )
    yield Result(state=State.OK, notice=f"Local identifier: {peer.local_identifier!r}")
    yield Result(state=State.OK, notice=f"Remote identifier: {peer.remote_identifier!r}")
    yield Result(state=State.OK, notice=f"Remote AS number: {peer.remote_as_number}")
    yield Result(state=State.OK, notice=f"Last received error: {peer.last_received_error!r}")
    yield Result(state=State.OK, notice=f"BGP version: {peer.bgp_version}")
    yield Result(state=State.OK, notice=f"Remote address: {item!r}")

    yield Metric("uptime", peer.established_time)


register.snmp_section(
    name="arista_bgp_peer",
    parse_function=parse_bgp_peer,
    parsed_section_name="bgp_peer",
    supersedes=["arista_bgp"],
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.30065.4.1.1",  # ARISTA-BGP4V2-MIB::aristaBgp4V2Objects
            oids=[
                OIDBytes("2.1.3"),  # LocalAddr
                OIDBytes("2.1.8"),  # LocalIdentifier
                "2.1.10",  # RemoteAs
                OIDBytes("2.1.11"),  # RemoteIdentifier
                "2.1.12",  # AdminStatus
                "2.1.13",  # State
                "3.1.4",  # LastErrorReceivedTex
                "4.1.1",  # FsmEstablishedTime
                "2.1.14",  # Description
                OIDEnd(),  # RemoteAddr
            ],
        )
    ],
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.30065"),
)

register.snmp_section(
    name="cisco_bgp_peerv2",
    parse_function=parse_bgp_peer_cisco_2,
    parsed_section_name="bgp_peer",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.187.1.2.5.1",  # CISCO-BGP4-MIB::cbgpPeer2Entry
            oids=[
                OIDBytes("6"),  # cbgpPeer2LocalAddr
                "9",  # cbgpPeer2LocalIdentifier
                "11",  # cbgpPeer2RemoteAs
                "12",  # cbgpPeer2RemoteIdentifier
                "4",  # cbgpPeer2AdminStatus
                "3",  # cbgpPeer2State
                "28",  # cbgpPeer2LastErrorTxt
                "19",  # cbgpPeer2FsmEstablishedTime
                OIDEnd(),  # cbgpPeer2RemoteAddr
            ],
        )
    ],
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1"),
        exists(".1.3.6.1.4.1.9.9.187.1.2.5.1.*"),
    ),
)
register.snmp_section(
    name="cisco_bgp_peerv3",
    parse_function=parse_bgp_peer_cisco_3,
    parsed_section_name="bgp_peer",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.187.1.2.9.1",  # CISCO-BGP4-MIB::cbgpPeer3Entry
            oids=[
                OIDBytes("8"),  # cbgpPeer3LocalAddr
                "11",  # cbgpPeer3LocalIdentifier
                "13",  # cbgpPeer3RemoteAs
                "14",  # cbgpPeer3RemoteIdentifier
                "6",  # cbgpPeer3AdminStatus
                "5",  # cbgpPeer3State
                "30",  # cbgpPeer3LastErrorTxt
                "21",  # cbgpPeer3FsmEstablishedTime
                "4",  # cbgpPeer3VrfName
                OIDEnd(),  # cbgpPeer3RemoteAddr
            ],
        )
    ],
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1"),
        exists(".1.3.6.1.4.1.9.9.187.1.2.9.1.*"),
    ),
)

register.check_plugin(
    name="bgp_peer",
    service_name="BGP Peer %s",
    discovery_function=discover_bgp_peer,
    check_function=check_bgp_peer,
    check_ruleset_name="bgp_peer",
    check_default_parameters=DEFAULT_BGP_PEER_PARAMS,
)
