#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<prtconf:sep(58):persist(1404743142)>>>
# System Model: IBM,8231-E2D
# Machine Serial Number: 06AAB2T
# Processor Type: PowerPC_POWER7
# Processor Implementation Mode: POWER 7
# Processor Version: PV_7_Compat
# Number Of Processors: 8
# Processor Clock Speed: 4284 MHz
# CPU Type: 64-bit
# Kernel Type: 64-bit
# LPAR Info: 1 wiaix001
# Memory Size: 257792 MB
# Good Memory Size: 257792 MB
# Platform Firmware level: AL770_076
# Firmware Version: IBM,AL770_076
# Console Login: enable
# Auto Restart: true
# Full Core: false
# Network Information
#        Host Name: example1
#        IP Address: 192.168.0.1
#        Sub Netmask: 255.255.255.128
#        Gateway: 192.168.0.2
#        Name Server: 192.168.0.3
#        Domain Name: example1.example.com
#
# Volume Groups Information
# Inactive VGs
# ==============================================================================
# appvg
# ==============================================================================
# Active VGs
# ==============================================================================
# cow-daag0cvg:
# PV_NAME           PV STATE          TOTAL PPs   FREE PPs    FREE DISTRIBUTION
# hdisk663          active            3218        0           00..00..00..00..00
# hdisk664          active            3218        0           00..00..00..00..00
# hdisk665          active            3218        0           00..00..00..00..00
# hdisk666          active            3218        0           00..00..00..00..00
# ==============================================================================
# Volume Groups Information
# Inactive VGs
# ==============================================================================
# appvg
# ==============================================================================
# Active VGs
# ==============================================================================
# free_alt_rootvg:
# PV_NAME           PV STATE          TOTAL PPs   FREE PPs    FREE DISTRIBUTION
# hdisk46           active            643         643         129..129..128..128..129
# ==============================================================================
# p2zgkbos4vg:
# PV_NAME           PV STATE          TOTAL PPs   FREE PPs    FREE DISTRIBUTION
# hdisk5            active            643         0           00..00..00..00..00
# hdisk18           active            643         0           00..00..00..00..00
# ==============================================================================
# INSTALLED RESOURCE LIST

# Note: this is only the header. Much more stuff follows, but is currently
# not being parsed.

from typing import TypedDict

from cmk.agent_based.v2 import AgentSection, Attributes, InventoryPlugin, StringTable, TableRow


def get_tuples_section(info):
    parsed = {}
    for line_info in info:
        if line_info[0] == "Volume Groups Information":
            break

        if not line_info:
            continue

        if len(line_info) == 2:
            key, value = line_info
            parsed[key] = value.strip()

    return parsed, info


def get_inactive_volume_groups(info):
    result = []
    begin_parsing = False
    for line_info in info:
        if line_info[0] == "Active VGs":
            break

        if line_info[0].startswith("Inactive VGs"):
            begin_parsing = True
            # On the line "Inactive VGs" hence skip two lines to get to the VG names
            next(info)
            continue

        if begin_parsing:
            if line_info[0].startswith("===="):
                begin_parsing = False
                continue

            result.append(line_info[0])

    return result, info


def get_active_volume_groups(info):
    result = []
    begin_parsing = False
    volume_group_name = ""
    temp = ""
    for line_info in info:
        if line_info[0].startswith("INSTALLED RESOURCE LIST"):
            break

        if line_info[0].startswith("PV_NAME"):
            begin_parsing = True
            volume_group_name = temp
            next(info)
            continue

        temp = line_info[0]

        if begin_parsing:
            if line_info[0].startswith("===="):
                begin_parsing = False
                continue

            result.append([volume_group_name] + line_info[0].split())

    return result


class SectionPRTConf(TypedDict):
    tuples: object
    inactive: object
    active: object


def parse_prtconf(string_table: StringTable) -> SectionPRTConf:
    parsed_tuples, info_remaining = get_tuples_section(iter(string_table))
    parsed_inactive, info_remaining = get_inactive_volume_groups(info_remaining)
    parsed_active = get_active_volume_groups(info_remaining)
    return {"tuples": parsed_tuples, "inactive": parsed_inactive, "active": parsed_active}


agent_section_prtconf = AgentSection(
    name="prtconf",
    parse_function=parse_prtconf,
)


def _split_vendor(string):
    if string.upper().startswith("IBM"):
        return "IBM", string[3:].lstrip("., -/")
    return "", string


def inv_prtconf(section):
    parsed_tuples = section["tuples"]
    if cpu_infos := _get_cpu_infos(parsed_tuples):
        yield Attributes(path=["hardware", "cpu"], inventory_attributes=cpu_infos)

    if sys_infos := _get_sys_infos(parsed_tuples):
        yield Attributes(path=["hardware", "system"], inventory_attributes=sys_infos)

    if mem_infos := _get_mem_infos(parsed_tuples):
        yield Attributes(path=["hardware", "memory"], inventory_attributes=mem_infos)

    if fmw_infos := _get_fmw_infos(parsed_tuples):
        yield Attributes(path=["software", "firmware"], inventory_attributes=fmw_infos)

    if net_infos := _get_net_infos(parsed_tuples):
        yield Attributes(path=["networking"], inventory_attributes=net_infos)

    if os_infos := _get_os_infos(parsed_tuples):
        yield Attributes(path=["software", "os"], inventory_attributes=os_infos)

    for key_columns, attrs in get_volume_groups(section):
        yield TableRow(
            path=["hardware", "volumes", "physical_volumes"],
            key_columns=key_columns,
            inventory_columns=attrs,
        )


def _get_cpu_infos(parsed_tuples):
    cpu_dict: dict[str, float | str] = {}

    cpu_type = parsed_tuples.get("CPU Type")
    if cpu_type is not None:
        cpu_dict["arch"] = "ppc64" if cpu_type == "64-bit" else "ppc"

    proc_type = parsed_tuples.get("Processor Type")
    if proc_type is not None:
        cpu_dict["model"] = proc_type

    proc_impl_mode = parsed_tuples.get("Processor Implementation Mode")
    if proc_impl_mode is not None:
        cpu_dict["implementation_mode"] = proc_impl_mode

    max_speed = parsed_tuples.get("Processor Clock Speed")
    if max_speed is not None:
        cpu_dict["max_speed"] = float(max_speed.split()[0]) * 1000 * 1000

    num_cpu = parsed_tuples.get("Number Of Processors")
    if num_cpu is not None:
        cpu_dict.setdefault("cpus", int(num_cpu))

    return cpu_dict


def _get_sys_infos(parsed_tuples):
    sys_dict = {}

    serial = parsed_tuples.get("Machine Serial Number")
    if serial is not None:
        sys_dict["serial"] = serial

    model = parsed_tuples.get("System Model")
    if model is not None:
        manufacturer, sys_dict["product"] = _split_vendor(model)
        if manufacturer:
            sys_dict["manufacturer"] = manufacturer

    return sys_dict


def _get_mem_infos(parsed_tuples):
    mem_dict = {}

    ram = parsed_tuples.get("Memory Size")
    if ram is not None:
        mem_dict["total_ram_usable"] = int(ram.split()[0]) * 1024 * 1024

    swap = parsed_tuples.get("Total Paging Space")
    if swap is not None:
        mem_dict["total_swap"] = int(swap.replace("MB", "")) * 1024 * 1024

    return mem_dict


def _get_fmw_infos(parsed_tuples):
    fmw_dict = {}

    fw_version = parsed_tuples.get("Firmware Version")
    if fw_version is not None:
        vendor, fmw_dict["version"] = _split_vendor(fw_version)
        if vendor:
            fmw_dict["vendor"] = vendor

    fw_platform_level = parsed_tuples.get("Platform Firmware level")
    if fw_platform_level is not None:
        fmw_dict["platform_level"] = fw_platform_level

    return fmw_dict


def _get_net_infos(parsed_tuples):
    net_dict = {}

    domain_name = parsed_tuples.get("Domain Name")
    if domain_name is not None:
        net_dict["domain_name"] = domain_name

    gateway = parsed_tuples.get("Gateway")
    if gateway is not None:
        net_dict["gateway"] = gateway

    ip_address = parsed_tuples.get("IP Address")
    if ip_address is not None:
        net_dict["ip_address"] = ip_address

    name_server = parsed_tuples.get("Name Server")
    if name_server is not None:
        net_dict["name_server"] = name_server

    sub_netmask = parsed_tuples.get("Sub Netmask")
    if sub_netmask is not None:
        net_dict["sub_netmask"] = sub_netmask

    return net_dict


def _get_os_infos(parsed_tuples):
    os_dict = {}

    kernel_type = parsed_tuples.get("Kernel Type")
    if kernel_type is not None:
        os_dict["arch"] = "ppc64" if kernel_type == "64-bit" else "ppc"

    return os_dict


def get_volume_groups(parsed):
    for item in parsed["active"]:
        vg_name, pv_name, pv_status, pv_total_partitions, pv_free_partitions, _pv_distr = item
        yield (
            {
                "volume_group_name": vg_name,
                "physical_volume_name": pv_name,
            },
            {
                "physical_volume_status": pv_status,
                "physical_volume_total_partitions": pv_total_partitions,
                "physical_volume_free_partitions": pv_free_partitions,
            },
        )

    for item in parsed["inactive"]:
        yield (
            {
                "volume_group_name": item,
                "physical_volume_name": "",
            },
            {
                "physical_volume_status": "Inactive",
                "physical_volume_total_partitions": "",
                "physical_volume_free_partitions": "",
            },
        )


inventory_plugin_prtconf = InventoryPlugin(
    name="prtconf",
    inventory_function=inv_prtconf,
)
