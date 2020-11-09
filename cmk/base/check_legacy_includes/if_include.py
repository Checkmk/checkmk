#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
import time
import collections

import cmk.base.plugins.agent_based.utils.interfaces as interfaces

from cmk.base.check_api import (
    check_levels,
    get_average,
    get_bytes_human_readable,
    get_nic_speed_human_readable,
    get_percent_human_readable,
    get_rate,
    host_name,
    MKCounterWrapped,
    RAISE,
    saveint,
)
# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
IF_CHECK_DEFAULT_PARAMETERS = interfaces.CHECK_DEFAULT_PARAMETERS

# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
Interface = collections.namedtuple("Interface", [
    "ifIndex",
    "ifGroup",
    "ifDescr",
    "ifType",
    "ifSpeed",
    "ifSpeed_as_text",
    "ifOperStatus",
    "ifOperStatusName",
    "ifInOctets",
    "inucast",
    "inmcast",
    "inbcast",
    "ifInDiscards",
    "ifInErrors",
    "ifOutOctets",
    "outucast",
    "outmcast",
    "outbcast",
    "ifOutDiscards",
    "ifOutErrors",
    "ifOutQLen",
    "ifAlias",
    "ifPhysAddress",
])


# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
def interface_from(line):
    (ifIndex, ifDescr, ifType, ifSpeed, ifOperStatus, ifInOctets, inucast, inmcast, inbcast,
     ifInDiscards, ifInErrors, ifOutOctets, outucast, outmcast, outbcast, ifOutDiscards,
     ifOutErrors, ifOutQLen, ifAlias, ifPhysAddress) = line

    # Windows NICs sends pairs of ifOperStatus and its Windows-Name instead
    # of just the ifOperStatus
    if isinstance(ifOperStatus, tuple):
        ifOperStatus, ifOperStatusName = ifOperStatus
    else:
        ifOperStatusName = if_statename(ifOperStatus)

    ifGroup = None
    if isinstance(ifIndex, tuple):
        ifGroup, ifIndex = ifIndex

    # Some devices (e.g. NetApp ONTAP) can report "auto" as speed
    if ifSpeed == "auto":
        ifSpeed_as_text = ifSpeed
    else:
        ifSpeed_as_text = None

    # Fix bug in TP Link switches
    ifSpeed = saveint(ifSpeed)
    if ifSpeed > 9 * 1000 * 1000 * 1000 * 1000:
        ifSpeed /= 1000000

    ifDescr = cleanup_if_strings(ifDescr)
    ifAlias = cleanup_if_strings(ifAlias)
    return Interface(ifIndex, ifGroup, ifDescr, ifType, ifSpeed, ifSpeed_as_text, ifOperStatus,
                     ifOperStatusName, ifInOctets, inucast, inmcast, inbcast, ifInDiscards,
                     ifInErrors, ifOutOctets, outucast, outmcast, outbcast, ifOutDiscards,
                     ifOutErrors, ifOutQLen, ifAlias, ifPhysAddress)


# Remove 0 bytes from strings. They lead to problems e.g. here:
# On windows hosts the labels of network interfaces in oid
# iso.3.6.1.2.1.2.2.1.2.1 are given as hex strings with tailing
# 0 byte. When this string is part of the data which is sent to
# the nagios pipe all chars after the 0 byte are stripped of.
# Stupid fix: Remove all 0 bytes. Hope this causes no problems.
# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
cleanup_if_strings = interfaces.cleanup_if_strings

# This variant of int() lets the string if its not
# convertable. Useful for parsing dict-like things, where
# some of the values are int.
# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
tryint = interfaces.tryint

# Name of state (lookup SNMP enum)
# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
if_statename = interfaces.statename


# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
def if_extract_node(line, has_nodeinfo):
    if has_nodeinfo:
        return line[0], line[1:]
    return None, line


# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
if_render_mac_address = interfaces.render_mac_address

# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
if_item_matches = interfaces.item_matches


# Pads port numbers with zeroes, so that items
# nicely sort alphabetically
# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
def if_pad_with_zeroes(info, ifIndex, has_nodeinfo, pad_portnumbers):
    if has_nodeinfo:
        index = 1
    else:
        index = 0
    if pad_portnumbers:

        def get_index(line):
            if isinstance(line[index], tuple):
                return line[index][1]
            return line[index]

        max_index = max([int(get_index(line)) for line in info])
        digits = len(str(max_index))
        return ("%0" + str(digits) + "d") % int(ifIndex)
    return ifIndex


# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
if_get_traffic_levels = interfaces.get_traffic_levels

# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
get_specific_traffic_levels = interfaces.get_specific_traffic_levels


# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
def _convert_old_if_group_params(params):
    if params["aggregate"] is True:
        del params["aggregate"]
        params.setdefault("aggregate", {})
        params["aggregate"].setdefault("group_patterns", {})
        params["aggregate"]["group_patterns"].setdefault(host_name(), {})

        for old_key, new_key in [
            ("include_items", "items"),
            ("iftype", "iftype"),
        ]:
            if params.get(old_key) is not None:
                params["aggregate"]["group_patterns"][host_name()].setdefault(
                    new_key, params[old_key])
                del params[old_key]

        if params.get("aggr_member_item") is not None:
            params["aggregate"].setdefault("item_type", params["aggr_member_item"])
            del params["aggr_member_item"]

    return params


# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
def _get_counter_name(node, name, item, group=None):
    if node is None:
        counter_name = "if.%s.%s" % (name, item)
    else:
        counter_name = "if.%s.%s.%s" % (node, name, item)

    if group is not None:
        counter_name += ".%s" % group

    return counter_name


# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
def check_if_common(item, params, info, has_nodeinfo=False, group_name="Group", timestamp=None):
    if timestamp is None:
        this_time = time.time()
    else:
        this_time = timestamp

    if not params.get("aggregate"):
        return check_if_common_single(item,
                                      params,
                                      info,
                                      has_nodeinfo=has_nodeinfo,
                                      timestamp=this_time)

    # If this item is in an ifgroup create a pseudo interface and
    # pass its data to the common instance.
    # This is done by simply adding the additional group_info data
    # to the already existing info table.
    params = _convert_old_if_group_params(params)
    group_members = {}
    matching_interfaces = []

    for element in info:
        node, line = if_extract_node(element, has_nodeinfo)
        interface = interface_from(line)

        service_name_type = params["aggregate"].get("item_type")
        if service_name_type == "description":
            if_member_item = interface.ifDescr
        elif service_name_type == "alias":
            if_member_item = interface.ifAlias
        else:  # index
            pad_portnumbers = item[0] == '0'
            if_member_item = if_pad_with_zeroes(info, interface.ifIndex, has_nodeinfo,
                                                pad_portnumbers)

        if interface.ifGroup and interface.ifGroup == item:
            matching_interfaces.append((if_member_item, element))

        else:
            if node is None:
                node = host_name()

            if node not in params["aggregate"]["group_patterns"]:
                continue

            attrs = params["aggregate"]["group_patterns"][node]
            node_items = attrs.get("items")
            iftype = attrs.get("iftype")

            # The iftype and node_items parameters are further restrictions
            # If none of them are set, the interface is added to the group
            # tryint -> force "01" and "1" to be identical.
            add_interface = True  # This approach is easier to comprehend..

            if node_items is not None and \
                tryint(if_member_item) not in map(tryint, node_items):
                add_interface = False

            if iftype is not None and \
                not saveint(interface.ifType) == saveint(iftype):
                add_interface = False

            this_element = (if_member_item, element)
            if add_interface and this_element not in matching_interfaces:
                matching_interfaces.append(this_element)

    # TODO Now we're done and have all matching interfaces
    # Accumulate info over matching_interfaces
    wrapped = False

    group_info = {
        "ifSpeed": 0,
        "ifInOctets": 0,
        "inucast": 0,
        "inmcast": 0,
        "inbcast": 0,
        "ifInDiscards": 0,
        "ifInErrors": 0,
        "ifOutOctets": 0,
        "outucast": 0,
        "outmcast": 0,
        "outbcast": 0,
        "ifOutDiscards": 0,
        "ifOutErrors": 0,
        "ifOutQLen": 0,
    }

    num_up = 0
    for (if_member_item, element) in matching_interfaces:
        node, line = if_extract_node(element, has_nodeinfo)
        interface = interface_from(line)

        # Append an additional entry to the info table containing the calculated group_info
        if interface.ifOperStatus == '1':
            num_up += 1

        group_members.setdefault(node, [])
        group_members[node].append({
            "name": if_member_item,
            "state": interface.ifOperStatus,
            "state_name": interface.ifOperStatusName,
        })

        # Only these values are packed into counters
        # We might need to enlarge this table
        # However, more values leads to more MKCounterWrapped...
        for name, counter in [
            ("in", interface.ifInOctets),
            ("inucast", interface.inucast),
            ("inmcast", interface.inmcast),
            ("inbcast", interface.inbcast),
            ("indisc", interface.ifInDiscards),
            ("inerr", interface.ifInErrors),
            ("out", interface.ifOutOctets),
            ("outucast", interface.outucast),
            ("outmcast", interface.outmcast),
            ("outbcast", interface.outbcast),
            ("outdisc", interface.ifOutDiscards),
            ("outerr", interface.ifOutErrors),
        ]:

            counter_name = _get_counter_name(node, name, item, group=if_member_item)

            try:
                get_rate(counter_name, this_time, saveint(counter), onwrap=RAISE)
            except MKCounterWrapped:
                wrapped = True
                # continue, other counters might wrap as well

        # Add interface info to group info
        group_info["ifSpeed"] += interface.ifOperStatus == "1" and interface.ifSpeed or 0
        group_info["ifInOctets"] += saveint(interface.ifInOctets)
        group_info["inucast"] += saveint(interface.inucast)
        group_info["inmcast"] += saveint(interface.inmcast)
        group_info["inbcast"] += saveint(interface.inbcast)
        group_info["ifInDiscards"] += saveint(interface.ifInDiscards)
        group_info["ifInErrors"] += saveint(interface.ifInErrors)
        group_info["ifOutOctets"] += saveint(interface.ifOutOctets)
        group_info["outucast"] += saveint(interface.outucast)
        group_info["outmcast"] += saveint(interface.outmcast)
        group_info["outbcast"] += saveint(interface.outbcast)
        group_info["ifOutDiscards"] += saveint(interface.ifOutDiscards)
        group_info["ifOutErrors"] += saveint(interface.ifOutErrors)
        group_info["ifOutQLen"] += saveint(interface.ifOutQLen)
        # This is the fallback ifType if None is set in the parameters
        group_info["ifType"] = interface.ifType

    if num_up == len(matching_interfaces):
        group_operStatus = "1"  # up
    elif num_up > 0:
        group_operStatus = "8"  # degraded
    else:
        group_operStatus = "2"  # down

    alias_info = []
    add_node_info = len(params["aggregate"].get("group_patterns", {})) >= 2

    for node_name, attrs in params["aggregate"].get("group_patterns", {}).items():
        if attrs.get("iftype"):
            alias_info.append("%sif type %s" % \
                                (add_node_info and "Node %s: " % node_name or "",
                                attrs["iftype"]))
            group_info["ifType"] = attrs["iftype"]

        if attrs.get("items"):
            alias_info.append("%d grouped interfaces" % len(matching_interfaces))

    if has_nodeinfo:
        group_entry = [None]
    else:
        group_entry = []

    group_entry += [
        "ifgroup%s" % item,  # ifIndex
        item,  # ifDescr
        group_info["ifType"],  # ifType
        group_info["ifSpeed"],  # ifSpeed
        group_operStatus,  # ifOperStatus
        group_info["ifInOctets"],  # ifInOctets
        group_info["inucast"],  # inucast
        group_info["inmcast"],  # inmcast
        group_info["inbcast"],  # inbcast
        group_info["ifInDiscards"],  # ifInDiscards
        group_info["ifInErrors"],  # ifInErrors
        group_info["ifOutOctets"],  # ifOutOctets
        group_info["outucast"],  # outucast
        group_info["outmcast"],  # outmcast
        group_info["outbcast"],  # outbcast
        group_info["ifOutDiscards"],  # ifOutDiscards
        group_info["ifOutErrors"],  # ifOutErrors
        group_info["ifOutQLen"],  # ifOutQLen
        ", ".join(alias_info),
        "",  # ifPhysAddress
    ]

    # If applicable, signal the check_if_common_single if the counter of the
    # given interface has wrapped. Actually a wrap of the if group itself is unlikely,
    # however any counter wrap of one of its members causes the accumulation being invalid
    return check_if_common_single(item,
                                  params, [group_entry],
                                  wrapped,
                                  has_nodeinfo=has_nodeinfo,
                                  group_members=group_members,
                                  group_name=group_name,
                                  timestamp=this_time)


# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
def _get_rate(counter, counter_name, timestamp, input_is_rate):
    if input_is_rate:
        if counter:
            return counter
        return 0.
    return get_rate(counter_name, timestamp, saveint(counter), onwrap=RAISE)


# TODO: Check what the relationship between Errors, Discards, and ucast/mcast actually is.
# One case of winperf_if appeared to indicate that in that case Errors = Discards.
# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/if.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO JOERG BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
def check_if_common_single(item,
                           params,
                           info,
                           force_counter_wrap=False,
                           has_nodeinfo=False,
                           group_members=None,
                           group_name="Group",
                           timestamp=None,
                           input_is_rate=False):

    if timestamp is None:
        this_time = time.time()
    else:
        this_time = timestamp

    # Params now must be a dict. Some keys might
    # be set to None
    targetspeed = params.get("speed")
    assumed_speed_in = params.get("assumed_speed_in")
    assumed_speed_out = params.get("assumed_speed_out")
    targetstates = params.get("state")
    map_operstates = dict(params.get("map_operstates", []))
    average = params.get("average")
    unit = "Bit" if params.get("unit") in ["Bit", "bit"] else "B"
    average_bmcast = params.get("average_bm")
    cluster_items = {}

    # error checking might be turned off
    err_warn, err_crit = params.get("errors", (None, None))
    err_in_warn, err_in_crit = params.get("errors_in", (err_warn, err_crit))
    err_out_warn, err_out_crit = params.get("errors_out", (err_warn, err_crit))

    # broadcast storm detection is turned off by default
    nucast_warn, nucast_crit = params.get("nucasts", (None, None))
    disc_warn, disc_crit = params.get("discards", (None, None))
    mcast_warn, mcast_crit = params.get("multicast", (None, None))
    bcast_warn, bcast_crit = params.get("broadcast", (None, None))

    # Convert the traffic related levels to a common format
    general_traffic_levels = if_get_traffic_levels(params)

    for line in info:
        node, line = if_extract_node(line, has_nodeinfo)
        interface = interface_from(line)

        if not if_item_matches(item, interface.ifIndex, interface.ifAlias, interface.ifDescr):
            continue

        if group_members:
            # The detailed group info is added later on
            infotext = group_name + " Status "
        else:
            if "infotext_format" in params:
                bracket_info = ""
                if params["infotext_format"] == "alias":
                    bracket_info = interface.ifAlias
                elif params["infotext_format"] == "description":
                    bracket_info = interface.ifDescr
                elif params["infotext_format"] == "alias_and_description":
                    bracket_info = ", ".join(
                        [i for i in [interface.ifAlias, interface.ifDescr] if i])
                elif params["infotext_format"] == "alias_or_description":
                    bracket_info = interface.ifAlias if interface.ifAlias else interface.ifDescr
                elif params["infotext_format"] == "desription_or_alias":
                    bracket_info = interface.ifDescr if interface.ifDescr else interface.ifAlias

                if bracket_info:
                    infotext = "[%s]" % bracket_info
                else:
                    infotext = ""
            else:
                # Display port number or alias in infotext if that is not part
                # of the service description anyway
                if item.lstrip("0") == interface.ifIndex \
                    and (item == interface.ifAlias or interface.ifAlias == '') \
                    and (item == interface.ifDescr or interface.ifDescr == ''): # description trivial
                    infotext = ""
                elif item == "%s %s" % (interface.ifAlias, interface.ifIndex
                                       ) and interface.ifDescr != '':  # non-unique Alias
                    infotext = "[%s/%s]" % (interface.ifAlias, interface.ifDescr)
                elif item != interface.ifAlias and interface.ifAlias != '':  # alias useful
                    infotext = "[%s] " % interface.ifAlias
                elif item != interface.ifDescr and interface.ifDescr != '':  # description useful
                    infotext = "[%s] " % interface.ifDescr
                else:
                    infotext = "[%s] " % interface.ifIndex

            if node is not None:
                infotext = "%son %s: " % (infotext, node)

        state = 0
        infotext += "(%s)" % interface.ifOperStatusName
        if targetstates and (
                interface.ifOperStatus != targetstates and
                not (isinstance(targetstates,
                                (list, tuple)) and interface.ifOperStatus in targetstates)):
            state = 2

        if map_operstates and interface.ifOperStatus in map_operstates:
            state = map_operstates[interface.ifOperStatus]

        if state == 1:
            infotext += "(!) "
        elif state == 2:
            infotext += "(!!) "
        elif state == 3:
            infotext += "(?) "
        else:
            infotext += " "

        if group_members:
            infotext = infotext[:-1]  # remove last space
            infotext += ", Members: "
            for group_node, members in group_members.items():
                member_info = []
                for member in members:
                    member_info.append("%s (%s)" % (member["name"], member["state_name"]))

                nodeinfo = ""
                if group_node is not None and len(group_members) > 1:
                    nodeinfo = " on node %s" % group_node
                infotext += "[%s%s] " % (", ".join(member_info), nodeinfo)

        if interface.ifPhysAddress:
            infotext += 'MAC: %s, ' % if_render_mac_address(interface.ifPhysAddress)

        # prepare reference speed for computing relative bandwidth usage
        speed = interface.ifSpeed
        if speed:
            ref_speed = speed / 8.0
        elif targetspeed:
            ref_speed = targetspeed / 8.0
        else:
            ref_speed = None

        # Check speed settings of interface, but only if speed information
        # is available. This is not always the case.
        if speed:
            infotext += get_nic_speed_human_readable(speed)
            if not targetspeed is None and speed != targetspeed:
                infotext += " (wrong speed, expected: %s)(!)" % get_nic_speed_human_readable(
                    targetspeed)
                state = max(state, 1)
        elif targetspeed:
            infotext += "assuming %s" % get_nic_speed_human_readable(targetspeed)
        elif interface.ifSpeed_as_text:
            infotext += "speed %s" % interface.ifSpeed_as_text
        else:
            infotext += "speed unknown"

        # Convert the traffic levels to interface specific levels, for example where the percentage
        # levels are converted to absolute levels or assumed speeds of an interface are treated correctly
        traffic_levels = get_specific_traffic_levels(general_traffic_levels, unit, ref_speed,
                                                     assumed_speed_in, assumed_speed_out)

        # Speed in bytes
        speed_b_in = (assumed_speed_in // 8) if assumed_speed_in else ref_speed
        speed_b_out = (assumed_speed_out // 8) if assumed_speed_out else ref_speed

        #
        # All internal values within this check after this point are bytes, not bits!
        #

        # When the interface is reported as down, there is no need to try to handle,
        # the performance counters. Most devices do reset the counter values to zero,
        # but we spotted devices, which do report error packes even for down interfaces.
        # To deal with it, we simply skip over all performance counter checks for down
        # interfaces.
        if str(interface.ifOperStatus) == "2":
            return state, infotext

        # Performance counters
        rates = []
        wrapped = False
        perfdata = []
        for name, counter, warn, crit, mmin, mmax in [
            ("in", interface.ifInOctets, traffic_levels[('in', 'upper', 'warn')],
             traffic_levels[('in', 'upper', 'crit')], 0, speed_b_in),
            ("inmcast", interface.inmcast, mcast_warn, mcast_crit, None, None),
            ("inbcast", interface.inbcast, bcast_warn, bcast_crit, None, None),
            ("inucast", interface.inucast, None, None, None, None),
            ("innucast", saveint(interface.inmcast) + saveint(interface.inbcast), nucast_warn,
             nucast_crit, None, None),
            ("indisc", interface.ifInDiscards, disc_warn, disc_crit, None, None),
            ("inerr", interface.ifInErrors, err_in_warn, err_in_crit, None, None),
            ("out", interface.ifOutOctets, traffic_levels[('out', 'upper', 'warn')],
             traffic_levels[('out', 'upper', 'crit')], 0, speed_b_out),
            ("outmcast", interface.outmcast, mcast_warn, mcast_crit, None, None),
            ("outbcast", interface.outbcast, bcast_warn, bcast_crit, None, None),
            ("outucast", interface.outucast, None, None, None, None),
            ("outnucast", saveint(interface.outmcast) + saveint(interface.outbcast), nucast_warn,
             nucast_crit, None, None),
            ("outdisc", interface.ifOutDiscards, disc_warn, disc_crit, None, None),
            ("outerr", interface.ifOutErrors, err_out_warn, err_out_crit, None, None),
        ]:

            counter_name = _get_counter_name(node, name, item)

            try:
                rate = _get_rate(counter, counter_name, timestamp, input_is_rate)
                if force_counter_wrap:
                    raise MKCounterWrapped("Forced counter wrap")
                rates.append(rate)
                perfdata.append((name, rate, warn, crit, mmin, mmax))
            except MKCounterWrapped:
                wrapped = True
                # continue, other counters might wrap as well

        # if at least one counter wrapped, we do not handle the counters at all
        if wrapped:
            # If there is a threshold on the bandwidth, we cannot proceed
            # further (the check would be flapping to green on a wrap)
            if any(traffic_levels.values()):
                raise MKCounterWrapped("Counter wrap, skipping checks this time")
            perfdata = []
        else:
            perfdata.append(("outqlen", saveint(interface.ifOutQLen)))

            def format_value(value):
                # TODO: one of these uses 1000 as base, the other 1024.
                # That is nasty, clean it up.
                if unit == "Bit":
                    return get_nic_speed_human_readable(value * 8)
                return "%s/s" % get_bytes_human_readable(value)

            # loop over incoming and outgoing traffic
            for what, traffic, mrate, brate, urate, nurate, discrate, errorrate, speed in [
                ("in", rates[0], rates[1], rates[2], rates[3], rates[4], rates[5], rates[6],
                 speed_b_in),
                ("out", rates[7], rates[8], rates[9], rates[10], rates[11], rates[12], rates[13],
                 speed_b_out)
            ]:
                if (what, 'predictive') in traffic_levels:
                    params = traffic_levels[(what, 'predictive')]
                    bw_warn, bw_crit = None, None
                else:
                    bw_warn = traffic_levels[(what, 'upper', 'warn')]
                    bw_crit = traffic_levels[(what, 'upper', 'crit')]
                    bw_warn_min = traffic_levels[(what, 'lower', 'warn')]
                    bw_crit_min = traffic_levels[(what, 'lower', 'crit')]
                    params = (bw_warn, bw_crit, bw_warn_min, bw_crit_min)

                # handle computation of average
                if average:
                    traffic_avg = get_average("if.%s.%s.avg" % (what, item), this_time, traffic,
                                              average)
                    dsname = "%s_avg_%d" % (what, average)
                    perfdata.append((dsname, traffic_avg, bw_warn, bw_crit, 0, speed))
                    traffic = traffic_avg  # apply levels to average traffic
                    title = "%s average %dmin" % (what.title(), average)
                else:
                    dsname = what
                    title = what.title()

                # Check bandwidth thresholds incl. prediction
                result = check_levels(traffic,
                                      dsname,
                                      params,
                                      statemarkers=True,
                                      human_readable_func=format_value,
                                      infoname=title)
                state = max(state, result[0])
                infotext += ", " + result[1]
                perfdata += result[2][1:]  # reference curve for predictive levels

                if speed:
                    perc_used = 100.0 * traffic / speed

                    assumed_info = ""
                    if assumed_speed_in or assumed_speed_out:
                        assumed_info = "/" + format_value(speed)
                    infotext += " (%.1f%%%s)" % (perc_used, assumed_info)

                # check error, broadcast, multicast and non-unicast packets and discards
                pacrate = urate + nurate + errorrate
                if pacrate > 0.0:  # any packets transmitted?
                    for value, params_warn, params_crit, text in [
                        (errorrate, err_warn, err_crit, "errors"),
                        (mrate, mcast_warn, mcast_crit, "multicast"),
                        (brate, bcast_warn, bcast_crit, "broadcast"),
                    ]:

                        calc_avg = False

                        infotxt = "%s-%s" % (what, text)
                        if average_bmcast is not None and text != "errors":
                            calc_avg = True
                            value_avg = get_average("if.%s.%s.%s.avg" % (what, text, item),
                                                    this_time, value, average_bmcast)
                            value = value_avg

                        perc_value = 100.0 * value / pacrate
                        if perc_value > 0:
                            if isinstance(params_crit, float):  # percentual levels
                                if calc_avg:
                                    infotxt += " average %dmin" % average_bmcast
                                result = check_levels(
                                    perc_value,
                                    dsname if text == "errors" else text,
                                    (params_warn, params_crit),
                                    statemarkers=True,
                                    human_readable_func=get_percent_human_readable,
                                    infoname=infotxt)
                            elif isinstance(params_crit, int):  # absolute levels
                                infotxt += " packets"
                                if calc_avg:
                                    infotxt += " average %dmin" % average_bmcast
                                result = check_levels(perc_value,
                                                      dsname, (params_warn, params_crit),
                                                      statemarkers=True,
                                                      human_readable_func=lambda x: "%d" % x,
                                                      infoname=infotxt)
                            state = max(state, result[0])
                            infotext += ", " + result[1]

                for _txt, _rate, _warn, _crit in [("non-unicast packets", nurate, nucast_warn,
                                                   nucast_crit),
                                                  ("discards", discrate, disc_warn, disc_crit)]:

                    if _crit is not None and _warn is not None:
                        result = check_levels(_rate,
                                              _txt, (_warn, _crit),
                                              statemarkers=True,
                                              unit="/s",
                                              infoname="%s %s" % (what, _txt))
                        state = max(state, result[0])
                        infotext += ", " + result[1]

        if node:
            cluster_items[node] = (state, infotext, perfdata)
        else:
            return (state, infotext, perfdata)

    # if system is a cluster we have more than one line per item with
    # different node, results are collected in cluster_items
    # we choose the node with the highest outgoing traffic
    # since in a cluster environment this is likely the node
    # which is master
    if cluster_items:
        maxval = 0
        choosen_node = None
        for node, result in cluster_items.items():
            state, infotext, perfdata = result
            for entry in perfdata:
                name, value = entry[:2]
                if name == "out":
                    maxval = max(maxval, value)
                    if maxval == value:
                        choosen_node = node
        # In case that each node has a counter wrap for
        # out, we use the last note from the list as source
        if not choosen_node:
            choosen_node = node
        return cluster_items[choosen_node]

    return 3, "No such interface"
