#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

from typing import List, Mapping, NamedTuple

from .agent_based_api.v1 import (
    OIDBytes,
    OIDEnd,
    register,
    Result,
    Service,
    SNMPTree,
    startswith,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringByteTable
from .utils.ip_format import clean_v4_address, clean_v6_address


class BGPData(NamedTuple):
    local_address: str
    local_identifier: str
    remote_as_number: int
    remote_identifier: str
    admin_state: str
    peer_state: str
    last_received_error: str
    bgp_version: int


Section = Mapping[str, BGPData]


def parse_arista_bgp(string_table: List[StringByteTable]) -> Section:
    def convert_address(value: str | list[int]) -> str:
        if not value:
            return "empty()"
        if isinstance(value, list):
            return clean_v4_address(value) if len(value) == 4 else clean_v6_address(value)
        split_value = value.split(".")
        return (
            clean_v4_address(split_value)
            if len(split_value) == 4
            else clean_v6_address(split_value)
        )

    def create_item_data(entry: list[str | list[int]]) -> BGPData:
        return BGPData(
            local_address=convert_address(entry[0]),
            local_identifier=convert_address(entry[1]),
            remote_as_number=int(entry[2]) if isinstance(entry[2], str) else 0,
            remote_identifier=convert_address(entry[3]),
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
            bgp_version=4,
        )

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
        addr_type = int(oid_elements[1])
        addr_len = int(oid_elements[2])
        assert len(oid_elements) == 3 + addr_len
        addr_elements = oid_elements[3 : 3 + addr_len]
        return (
            clean_v4_address(addr_elements) if addr_type == 1 else clean_v6_address(addr_elements)
        )

    assert all(
        len(entry) == len(BGPData.__annotations__) for entry in string_table[0]
    ), "Not all info elements have the size guessed from known names %d: %r" % (
        len(BGPData.__annotations__),
        [len(entry) for entry in string_table[0]],
    )
    return {remote_addr(str(entry[-1])): create_item_data(entry) for entry in string_table[0]}


def discover_arista_bgp(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_arista_bgp(
    item: str,
    section: Section,
) -> CheckResult:
    if not (peer := section.get(item)):
        return
    yield Result(state=State.OK, summary=f"Local address: {peer.local_address!r}")
    yield Result(state=State.OK, summary=f"Local identifier: {peer.local_identifier!r}")
    yield Result(state=State.OK, summary=f"Remote AS number: {peer.remote_as_number}")
    yield Result(state=State.OK, summary=f"Remote identifier: {peer.remote_identifier!r}")
    yield Result(state=State.OK, summary=f"Admin state: {peer.admin_state!r}")
    yield Result(state=State.OK, summary=f"Peer state: {peer.peer_state!r}")
    yield Result(state=State.OK, summary=f"Last received error: {peer.last_received_error!r}")
    yield Result(state=State.OK, summary=f"BGP version: {peer.bgp_version}")
    yield Result(state=State.OK, summary=f"Remote address: {item!r}")


register.snmp_section(
    name="arista_bgp_peer",
    parse_function=parse_arista_bgp,
    parsed_section_name="arista_bgp",
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
                OIDEnd(),  # RemoteAddr
            ],
        )
    ],
    detect=startswith(".1.3.6.1.2.1.1.1.0", "arista networks"),
)

register.check_plugin(
    name="arista_bgp",
    service_name="BGP Peer %s",
    discovery_function=discover_arista_bgp,
    check_function=check_arista_bgp,
)
