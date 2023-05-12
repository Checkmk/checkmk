#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import check_levels, get_parsed_item_data, get_percent_human_readable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info, factory_settings


def inventory_ucs_c_rack_server_util(parsed):
    """
    Yields indexed racks as items (e.g. Rack Unit 1).
    """
    for key in parsed:
        yield key, {}


##########################
# ucs_c_rack_server_util #
##########################

factory_settings["ucs_c_rack_server_util_overall_default_levels"] = {
    "upper_levels": (90.0, 95.0),
}


@get_parsed_item_data
def check_ucs_c_rack_server_util(item, params, data):
    # None values passed to check_levels(value, ...) are handled by Checkmk internals appropriatelly.
    if (overall_util := data.overall) is None:
        return
    yield check_levels(
        overall_util,
        "overall_util",
        params["upper_levels"],
        human_readable_func=get_percent_human_readable,
    )


check_info["ucs_c_rack_server_util"] = {
    "discovery_function": inventory_ucs_c_rack_server_util,
    "check_function": check_ucs_c_rack_server_util,
    "check_ruleset_name": "overall_utilization_multiitem",
    "service_name": "Overall Utilization %s",
    "default_levels_variable": "ucs_c_rack_server_util_overall_default_levels",
}

##############################
# ucs_c_rack_server_util.cpu #
##############################

factory_settings["ucs_c_rack_server_util_cpu_default_levels"] = {
    "levels": (90.0, 95.0),
}


@get_parsed_item_data
def check_ucs_c_rack_server_util_cpu(item, params, data):
    if (cpu_util := data.cpu) is None:
        return None
    return check_cpu_util(cpu_util, params)


check_info["ucs_c_rack_server_util.cpu"] = {
    "discovery_function": inventory_ucs_c_rack_server_util,
    "check_function": check_ucs_c_rack_server_util_cpu,
    "check_ruleset_name": "cpu_utilization_multiitem",
    "service_name": "CPU Utilization %s",
    "default_levels_variable": "ucs_c_rack_server_util_cpu_default_levels",
}

#################################
# ucs_c_rack_server_util.pci_io #
#################################

factory_settings["ucs_c_rack_server_util_pci_io_default_levels"] = {
    "upper_levels": (90.0, 95.0),
}


@get_parsed_item_data
def check_ucs_c_rack_server_util_pci_io(item, params, data):
    if (io_util := data.io) is None:
        return
    yield check_levels(
        io_util,
        "pci_io_util",
        params["upper_levels"],
        human_readable_func=get_percent_human_readable,
    )


check_info["ucs_c_rack_server_util.pci_io"] = {
    "discovery_function": inventory_ucs_c_rack_server_util,
    "check_function": check_ucs_c_rack_server_util_pci_io,
    "check_ruleset_name": "pci_io_utilization_multiitem",
    "service_name": "PCI IO Utilization %s",
    "default_levels_variable": "ucs_c_rack_server_util_pci_io_default_levels",
}

##############################
# ucs_c_rack_server_util.mem #
##############################

factory_settings["ucs_c_rack_server_util_mem_default_levels"] = {
    "upper_levels": (90.0, 95.0),
}


@get_parsed_item_data
def check_ucs_c_rack_server_util_mem(item, params, data):
    if (memory_util := data.memory) is None:
        return
    yield check_levels(
        memory_util,
        "memory_util",
        params["upper_levels"],
        human_readable_func=get_percent_human_readable,
    )


check_info["ucs_c_rack_server_util.mem"] = {
    "discovery_function": inventory_ucs_c_rack_server_util,
    "check_function": check_ucs_c_rack_server_util_mem,
    "check_ruleset_name": "memory_utilization_multiitem",
    "service_name": "Memory Utilization %s",
    "default_levels_variable": "ucs_c_rack_server_util_mem_default_levels",
}
