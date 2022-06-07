#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any, List, Mapping, MutableMapping, Optional, Sequence, Tuple, TypedDict, Union

from .agent_based_api.v1 import get_value_store, register, Result
from .agent_based_api.v1 import State as state
from .agent_based_api.v1 import type_defs
from .utils import interfaces, netapp_api

MACList = List[Tuple[str, Optional[str]]]


class NICExtraInfo(TypedDict, total=False):
    grouped_if: MACList
    speed_differs: Tuple[int, int]
    home_port: str
    is_home: bool


ExtraInfo = Mapping[str, NICExtraInfo]
Section = Tuple[interfaces.Section, ExtraInfo]


def parse_netapp_api_if(  # pylint: disable=too-many-branches
    string_table: type_defs.StringTable,
) -> Section:
    ifaces = netapp_api.parse_netapp_api_single_instance(string_table)

    # Dictionary with lists of common mac addresses
    if_mac_list: MutableMapping[str, MACList] = {}
    # List of virtual interfaces
    vif_list = []

    speed: Union[str, int]

    # Calculate speed, state and create mac-address list
    for name, values in ifaces.items():
        # Reported by 7Mode
        mediatype = values.get("mediatype")
        if mediatype:
            tokens = mediatype.split("-")
            # Possible values according to 7-Mode docu: 100tx | 100tx-fd | 1000fx | 10g-sr
            if "1000" in mediatype:
                speed = 1000000000
            elif "100" in mediatype:
                speed = 100000000
            elif "10g" in mediatype:
                speed = 10000000000
            elif "10" in mediatype:
                speed = 10000000
            else:
                speed = 0
            values["speed"] = str(speed)

            values["state"] = "1" if tokens[-1].lower() == "up" else "2"
        elif values.get("port-role") != "storage-acp":
            # If an interface has no media type and is not a storage-acp, it is considered as
            # virtual interface
            vif_list.append(name)

        # Reported by Clustermode
        for status_key in ["link-status", "operational-status"]:
            if status_key in values:
                if values[status_key] == "up":
                    values["state"] = "1"
                else:
                    values["state"] = "2"
                break

        # Reported by Clustermode
        if "operational-speed" in values:
            raw_speed = values["operational-speed"]
            if raw_speed == "auto":
                # For ONTAP systems, we may receive "auto" for the operational speed
                values["speed"] = raw_speed
            else:
                values["speed"] = str(int(raw_speed) * 1000 * 1000)

        if "mac-address" in values:
            if_mac_list.setdefault(values["mac-address"], [])
            if_mac_list[values["mac-address"]].append((name, values.get("state")))

    nics = []
    extra_info: MutableMapping[str, NICExtraInfo] = {}
    for idx, (nic_name, values) in enumerate(sorted(ifaces.items())):
        speed = values.get("speed", 0)

        # Try to determine the speed and state for virtual interfaces
        # We know all physical interfaces for this virtual device and use the highest available
        # speed as the virtual speed. Note: Depending on the configuration this behaviour might
        # differ, e.g. the speed of all interfaces might get accumulated..
        # Additionally, we check if not all interfaces of the virtual group share the same
        # connection speed
        if not speed:
            if "mac-address" in values:
                mac_list = if_mac_list[values["mac-address"]]
                if len(mac_list) > 1:  # check if this interface is grouped
                    extra_info.setdefault(nic_name, {})
                    extra_info[nic_name]["grouped_if"] = [
                        x for x in mac_list if x[0] not in vif_list
                    ]

                    max_speed = 0
                    min_speed = 1024**5
                    for tmp_if, _ in mac_list:
                        if tmp_if == nic_name or "speed" not in ifaces[tmp_if]:
                            continue
                        check_speed = int(ifaces[tmp_if]["speed"])
                        max_speed = max(max_speed, check_speed)
                        min_speed = min(min_speed, check_speed)
                    if max_speed != min_speed:
                        extra_info[nic_name]["speed_differs"] = (max_speed, min_speed)
                    speed = max_speed

        # Virtual interfaces is "Up" if at least one physical interface is up
        if "state" in values:
            oper_status = values["state"]
        else:
            oper_status = "2"
            if "mac-address" in values:
                for tmp_if, tmp_oper_status in if_mac_list[values["mac-address"]]:
                    if tmp_oper_status == "1":
                        oper_status = "1"
                        break

        # Only add interfaces with counters
        if "recv_data" in values:
            nics.append(
                interfaces.Interface(
                    index=str(idx + 1),
                    descr=nic_name,
                    alias=values.get("interface-name", ""),
                    type="6",
                    speed=interfaces.saveint(speed),
                    oper_status=oper_status,
                    in_octets=interfaces.saveint(values.get("recv_data")),
                    in_ucast=interfaces.saveint(values.get("recv_packet")),
                    in_mcast=interfaces.saveint(values.get("recv_mcasts")),
                    in_errors=interfaces.saveint(values.get("recv_errors")),
                    out_octets=interfaces.saveint(values.get("send_data")),
                    out_ucast=interfaces.saveint(values.get("send_packet")),
                    out_mcast=interfaces.saveint(values.get("send_mcasts")),
                    out_errors=interfaces.saveint(values.get("send_errors")),
                    phys_address=interfaces.mac_address_from_hexstring(
                        values.get("mac-address", "")
                    ),
                    speed_as_text=speed == "auto" and "auto" or "",
                )
            )
            if "home-port" in values:
                extra_info.setdefault(nic_name, {}).update(
                    {
                        "home_port": values["home-port"],
                        "is_home": values.get("is-home") == "true",
                    }
                )

    return nics, extra_info


register.agent_section(
    name="netapp_api_if",
    parse_function=parse_netapp_api_if,
)


def discover_netapp_api_if(
    params: Sequence[Mapping[str, Any]],
    section: Section,
) -> type_defs.DiscoveryResult:
    yield from interfaces.discover_interfaces(
        params,
        section[0],
    )


STATUS_MAP = {
    "check_and_crit": 2,
    "check_and_warn": 1,
    "check_and_display": 0,
}
INFO_INCLUDED_MAP = {"dont_show_and_check": False}


def check_netapp_api_if(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    yield from _check_netapp_api_if(item, params, section, get_value_store())


def _check_netapp_api_if(  # pylint: disable=too-many-branches
    item: str,
    params: Mapping[str, Any],
    section: Section,
    value_store: MutableMapping[str, Any],
) -> type_defs.CheckResult:
    nics, extra_info = section
    yield from interfaces.check_multiple_interfaces(
        item,
        params,
        nics,
        value_store=value_store,
    )

    for iface in nics:
        descr_cln = interfaces.cleanup_if_strings(iface.descr)
        alias_cln = interfaces.cleanup_if_strings(iface.alias)
        first_member = True
        if interfaces.item_matches(item, iface.index, alias_cln, descr_cln):
            vif = extra_info.get(iface.descr)
            if vif is None:
                continue

            speed_state, speed_info_included = 1, True
            home_state, home_info_included = 0, True

            if "match_same_speed" in params:
                speed_behaviour = params["match_same_speed"]
                speed_info_included = INFO_INCLUDED_MAP.get(
                    speed_behaviour,
                    speed_info_included,
                )
                speed_state = STATUS_MAP.get(speed_behaviour, speed_state)

            if "home_port" in params:
                home_behaviour = params["home_port"]
                home_info_included = INFO_INCLUDED_MAP.get(home_behaviour, home_info_included)
                home_state = STATUS_MAP.get(home_behaviour, home_state)

            if "home_port" in vif and home_info_included:
                is_home_port = vif["is_home"]
                mon_state = 0 if is_home_port else home_state
                home_attribute = "is %shome port" % ("" if is_home_port else "not ")
                yield Result(
                    state=state(mon_state),
                    summary="Current Port: %s (%s)" % (vif["home_port"], home_attribute),
                )

            if "grouped_if" in vif:
                for member_name, member_state in sorted(vif.get("grouped_if", [])):
                    if member_state is None or member_name == iface.descr:
                        continue  # Not a real member or the grouped interface itself

                    if member_state == "2":
                        mon_state = 1
                    else:
                        mon_state = 0

                    if first_member:
                        yield Result(
                            state=state(mon_state),
                            summary="Physical interfaces: %s(%s)"
                            % (
                                member_name,
                                interfaces.statename(member_state),
                            ),
                        )
                        first_member = False
                    else:
                        yield Result(
                            state=state(mon_state),
                            summary="%s(%s)" % (member_name, interfaces.statename(member_state)),
                        )

            if "speed_differs" in vif and speed_info_included:
                yield Result(
                    state=state(speed_state),
                    summary="Interfaces do not have the same speed",
                )


register.check_plugin(
    name="netapp_api_if",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_netapp_api_if,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_netapp_api_if,
)
