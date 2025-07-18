#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.base.check_legacy_includes.scaleio import convert_scaleio_space
from cmk.plugins.lib.scaleio import parse_scaleio, ScaleioSection

check_info = {}

# example output
# <<<scaleio_sds>>>
# SDS 3c7af8db00000000:
#        ID                                                 3c7af8db00000000
#        NAME                                               sds03
#        PROTECTION_DOMAIN_ID                               91ebcf4500000000
#        STATE                                              REMOVE_STATE_NORMAL
#        MEMBERSHIP_STATE                                   JOINED
#        MDM_CONNECTION_STATE                               MDM_CONNECTED
#        MAINTENANCE_MODE_STATE                             NO_MAINTENANCE
#        MAX_CAPACITY_IN_KB                                 21.8 TB (22353 GB)
#        UNUSED_CAPACITY_IN_KB                              13.2 TB (13471 GB)
#
# SDS 3c7ad1cc00000001:
#        ID                                                 3c7ad1cc00000001
#        NAME                                               sds01
#        PROTECTION_DOMAIN_ID                               91ebcf4500000000
#        STATE                                              REMOVE_STATE_NORMAL
#        MEMBERSHIP_STATE                                   JOINED
#        MDM_CONNECTION_STATE                               MDM_CONNECTED
#        MAINTENANCE_MODE_STATE                             NO_MAINTENANCE
#        MAX_CAPACITY_IN_KB                                 21.8 TB (22353 GB)
#        UNUSED_CAPACITY_IN_KB                              13.2 TB (13477 GB)
#
# SDS 3c7af8dc00000002:
#        ID                                                 3c7af8dc00000002
#        NAME                                               sds02
#        PROTECTION_DOMAIN_ID                               91ebcf4500000000
#        STATE                                              REMOVE_STATE_NORMAL
#        MEMBERSHIP_STATE                                   JOINED
#        MDM_CONNECTION_STATE                               MDM_CONNECTED
#        MAINTENANCE_MODE_STATE                             NO_MAINTENANCE
#        MAX_CAPACITY_IN_KB                                 21.8 TB (22353 GB)
#        UNUSED_CAPACITY_IN_KB                              13.2 TB (13477 GB)
#


def parse_scaleio_sds(string_table: StringTable) -> ScaleioSection:
    return parse_scaleio(string_table, "SDS")


def inventory_scaleio_sds(parsed):
    for entry in parsed:
        yield entry, {}


def check_scaleio_sds(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    # How will the data be represented? It's magic and the only
    # indication is the unit. We need to handle this!
    unit = data["MAX_CAPACITY_IN_KB"][3].strip(")")
    total = convert_scaleio_space(unit, int(data["MAX_CAPACITY_IN_KB"][2].strip("(")))
    free = convert_scaleio_space(unit, int(data["UNUSED_CAPACITY_IN_KB"][2].strip("(")))

    yield df_check_filesystem_list(item, params, [(item, total, free, 0)])


check_info["scaleio_sds"] = LegacyCheckDefinition(
    name="scaleio_sds",
    parse_function=parse_scaleio_sds,
    service_name="ScaleIO SDS capacity %s",
    discovery_function=inventory_scaleio_sds,
    check_function=check_scaleio_sds,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)


def inventory_scaleio_sds_status(parsed):
    for entry in parsed:
        yield entry, {}


def check_scaleio_sds_status(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return

    name, pd_id = data["NAME"][0], data["PROTECTION_DOMAIN_ID"][0]
    yield 0, f"Name: {name}, PD: {pd_id}"

    status = data["STATE"][0]
    if "normal" not in status.lower():
        yield 2, "State: %s" % status

    status_maint = data["MAINTENANCE_MODE_STATE"][0]
    if "no_maintenance" not in status_maint.lower():
        yield 1, "Maintenance: %s" % status_maint

    status_conn = data["MDM_CONNECTION_STATE"][0]
    if "connected" not in status_conn.lower():
        yield 2, "Connection state: %s" % status_conn

    status_member = data["MEMBERSHIP_STATE"][0]
    if "joined" not in status_member.lower():
        yield 2, "Membership state: %s" % status_member


check_info["scaleio_sds.status"] = LegacyCheckDefinition(
    name="scaleio_sds_status",
    service_name="ScaleIO SDS status %s",
    sections=["scaleio_sds"],
    discovery_function=inventory_scaleio_sds_status,
    check_function=check_scaleio_sds_status,
)
