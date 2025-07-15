#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.base.check_legacy_includes.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

check_info = {}

# Example output from agent:
# [zmucvm99-lds]
# accessible  True
# capacity    578478407680
# freeSpace   388398841856
# type    VMFS
# uncommitted 51973812224
# url /vmfs/volumes/513df1e9-12fd7366-ac5a-e41f13e69eaa


def parse_esx_vsphere_datastores(string_table):
    stores = {}
    for line in string_table:
        if line[0].startswith("["):
            name = line[0][1:-1]
            store = {}
            stores[name] = store
        else:
            # Seems that the url attribute can have an empty value
            if len(line) == 1:
                key = line[0].strip()
                value = None
            else:
                key, value = line

            if key == "accessible" and value is not None:
                value = value.lower() == "true"
            elif key in ["capacity", "freeSpace", "uncommitted"] and value is not None:
                value = int(value)
            store[key] = value
    return stores


def check_esx_vsphere_datastores(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    if not data["accessible"]:
        yield 2, "inaccessible"

    mib = 1024.0**2
    size_bytes = data.get("capacity")
    avail_bytes = data.get("freeSpace")
    if size_bytes is None or size_bytes == 0 or avail_bytes is None:
        return

    yield df_check_filesystem_single(
        item, size_bytes / mib, avail_bytes / mib, 0, None, None, params
    )  # fixed: true-division

    uncommitted_bytes = data.get("uncommitted")
    if uncommitted_bytes is None:
        return
    text_uncommitted = "Uncommitted: %s" % render.bytes(uncommitted_bytes)
    yield 0, text_uncommitted, [("uncommitted", uncommitted_bytes / mib)]  # fixed: true-division

    used_bytes = size_bytes - avail_bytes
    prov_bytes = used_bytes + uncommitted_bytes
    prov_percent = (prov_bytes * 100.0) / size_bytes if size_bytes != 0 else 0

    warn, crit = params.get("provisioning_levels", (None, None))
    yield check_levels(
        prov_percent,
        None,
        (warn, crit),
        human_readable_func=render.percent,
        infoname="Provisioning",
    )

    if prov_bytes > size_bytes:
        prov_used = used_bytes / prov_bytes * 100.0
        yield 0, f"{render.percent(prov_used)} provisioned space used"

    if warn is not None:
        # convert percent to abs MiB
        scale = (size_bytes / mib) / 100.0  # fixed: true-division
        yield (
            0,
            "",
            [("overprovisioned", prov_bytes / mib, scale * warn, scale * crit)],
        )  # fixed: true-division
    else:
        yield 0, "", [("overprovisioned", prov_bytes / mib)]  # fixed: true-division


def discover_esx_vsphere_datastores(section):
    yield from ((item, {}) for item in section)


check_info["esx_vsphere_datastores"] = LegacyCheckDefinition(
    name="esx_vsphere_datastores",
    parse_function=parse_esx_vsphere_datastores,
    service_name="Filesystem %s",
    discovery_function=discover_esx_vsphere_datastores,
    check_function=check_esx_vsphere_datastores,
    check_ruleset_name="esx_vsphere_datastores",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)

# .
