#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.emcvnx import preparse_emcvnx_info

check_info = {}

# Example output from agent:
# <<<emcvnx_info>>>
#
#
# Server IP Address:       10.1.36.13
# Agent Rev:           7.32.25 (1.56)
#
#
# Agent/Host Information
# -----------------------
#
#
#
# Agent Rev:           7.32.25 (1.56)
# Name:                K10
# Desc:
# Node:                A-CKM00114701225
# Physical Node:       K10
# Signature:           3195192
# Peer Signature:      3187006
# Revision:            05.32.000.5.201
# SCSI Id:             0
# Model:               VNX5300
# Model Type:          Rackmount
# Prom Rev:            7.00.00
# SP Memory:           8192
# Serial No:           CKM00114701225
# SP Identifier:       A
# Cabinet:             DPE7
#
# Name of the software package:        -Compression
# Revision of the software package:    -
# Commit Required:                     NO
# Revert Possible:                     NO
# Active State:                        YES
# Is installation completed:           YES
# Is this System Software:             NO
#
# [... more software packages follow ...]


def parse_emcvnx_info(string_table):
    parsed = {
        "info": [],
        "storage": [],
        "link": [],
        "config": [],
        "io": [],
    }
    key_to_subcheck = {
        "System Fault LED": "info",
        "Server IP Address": "info",
        "System Date": "info",
        "System Time": "info",
        "Serial Number For The SP": "info",
        "Storage Processor": "storage",
        "Storage Processor Network Name": "storage",
        "Storage Processor IP Address": "storage",
        "Storage Processor Subnet Mask": "storage",
        "Storage Processor Gateway Address": "storage",
        "Storage Processor IPv6 Mode": "storage",
        "Link Status": "link",
        "Current Speed": "link",
        "Requested Speed": "link",
        "Auto-Negotiate": "link",
        "Capable Speeds": "link",
        "Statistics Logging": "config",
        "SP Read Cache State": "config",
        "SP Write Cache State": "config",
        "Hw_flush_on": "config",
        "Idle_flush_on": "config",
        "Lw_flush_off": "config",
        "Max Requests": "io",
        "Average Requests": "io",
        "Hard errors": "io",
        "Total Reads": "io",
        "Total Writes": "io",
        "Read_requests": "io",
        "Write_requests": "io",
        "Blocks_read": "io",
        "Blocks_written": "io",
        "Sum_queue_lengths_by_arrivals": "io",
        "Arrivals_to_non_zero_queue": "io",
        "Write_cache_flushes": "io",
        "Write_cache_blocks_flushed": "io",
    }

    preparsed, errors = preparse_emcvnx_info(string_table)

    for key, value in preparsed:
        subcheck = key_to_subcheck.get(key)
        if subcheck:
            parsed[subcheck].append((key, value))
    return parsed, errors


def inventory_emcvnx_info(parsed, subcheck):
    output, _errors = parsed
    if output[subcheck]:
        return [(None, None)]
    return []


#   .--Info----------------------------------------------------------------.
#   |                         ___        __                                |
#   |                        |_ _|_ __  / _| ___                           |
#   |                         | || '_ \| |_ / _ \                          |
#   |                         | || | | |  _| (_) |                         |
#   |                        |___|_| |_|_|  \___/                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_emcvnx_info(item, _no_params, parsed):
    output, errors = parsed

    if errors:
        yield (
            2,
            (
                "Error(s) while parsing the output. This may effect the "
                "discovery of other emcvnx services. Please check your naviseccli "
                "configuration. Errors are: %s" % (" ".join(errors))
            ),
        )

    for key, value in output["info"]:
        status = 0
        if key == "System Fault LED" and value != "OFF":
            status = 2
        yield status, f"{key}: {value}"


def discover_emcvnx_info(x):
    return inventory_emcvnx_info(x, "info")


check_info["emcvnx_info"] = LegacyCheckDefinition(
    name="emcvnx_info",
    parse_function=parse_emcvnx_info,
    service_name="EMC VNX Info",
    discovery_function=discover_emcvnx_info,
    check_function=check_emcvnx_info,
)

#   .--Storage-------------------------------------------------------------.
#   |                 ____  _                                              |
#   |                / ___|| |_ ___  _ __ __ _  __ _  ___                  |
#   |                \___ \| __/ _ \| '__/ _` |/ _` |/ _ \                 |
#   |                 ___) | || (_) | | | (_| | (_| |  __/                 |
#   |                |____/ \__\___/|_|  \__,_|\__, |\___|                 |
#   |                                          |___/                       |
#   '----------------------------------------------------------------------'


def check_emcvnx_storage(item, params, parsed):
    output, _ = parsed
    for key, value in output["storage"]:
        yield 0, f"{key}: {value}"


def discover_emcvnx_info_storage(x):
    return inventory_emcvnx_info(x, "storage")


check_info["emcvnx_info.storage"] = LegacyCheckDefinition(
    name="emcvnx_info_storage",
    service_name="EMC VNX Storage Processor",
    sections=["emcvnx_info"],
    discovery_function=discover_emcvnx_info_storage,
    check_function=check_emcvnx_storage,
)

#   .--Link----------------------------------------------------------------.
#   |                         _     _       _                              |
#   |                        | |   (_)_ __ | | __                          |
#   |                        | |   | | '_ \| |/ /                          |
#   |                        | |___| | | | |   <                           |
#   |                        |_____|_|_| |_|_|\_\                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_emcvnx_link(item, params, parsed):
    output, _ = parsed
    for key, value in output["link"]:
        status = 0
        if key == "Link Status" and value != "Link-Up":
            status = 2
        yield status, f"{key}: {value}"


def discover_emcvnx_info_link(x):
    return inventory_emcvnx_info(x, "link")


check_info["emcvnx_info.link"] = LegacyCheckDefinition(
    name="emcvnx_info_link",
    service_name="EMC VNX Link",
    sections=["emcvnx_info"],
    discovery_function=discover_emcvnx_info_link,
    check_function=check_emcvnx_link,
)

#   .--Config--------------------------------------------------------------.
#   |                     ____             __ _                            |
#   |                    / ___|___  _ __  / _(_) __ _                      |
#   |                   | |   / _ \| '_ \| |_| |/ _` |                     |
#   |                   | |__| (_) | | | |  _| | (_| |                     |
#   |                    \____\___/|_| |_|_| |_|\__, |                     |
#   |                                           |___/                      |
#   '----------------------------------------------------------------------'


def check_emcvnx_config(item, params, parsed):
    output, _ = parsed
    for key, value in output["config"]:
        yield 0, f"{key}: {value}"


def discover_emcvnx_info_config(x):
    return inventory_emcvnx_info(x, "config")


check_info["emcvnx_info.config"] = LegacyCheckDefinition(
    name="emcvnx_info_config",
    service_name="EMC VNX Config",
    sections=["emcvnx_info"],
    discovery_function=discover_emcvnx_info_config,
    check_function=check_emcvnx_config,
)

#   .--IO------------------------------------------------------------------.
#   |                              ___ ___                                 |
#   |                             |_ _/ _ \                                |
#   |                              | | | | |                               |
#   |                              | | |_| |                               |
#   |                             |___\___/                                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_emcvnx_io(item, params, parsed):
    output, _ = parsed
    for key, value in output["io"]:
        status = 0
        if key == "Hard errors" and value != "N/A":
            status = 2
        yield status, f"{key}: {value}"


def discover_emcvnx_info_io(x):
    return inventory_emcvnx_info(x, "io")


check_info["emcvnx_info.io"] = LegacyCheckDefinition(
    name="emcvnx_info_io",
    service_name="EMC VNX IO",
    sections=["emcvnx_info"],
    discovery_function=discover_emcvnx_info_io,
    check_function=check_emcvnx_io,
)
