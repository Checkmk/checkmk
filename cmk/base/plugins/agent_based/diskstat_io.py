#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Mapping, MutableMapping, Optional

from .agent_based_api.v1 import get_value_store, register, Result, State, type_defs
from .utils import diskstat, hp_msa


def _check_disk(
    params: Mapping[str, Any],
    disk: diskstat.Disk,
    value_store: MutableMapping[str, Any],
    now: float,
) -> type_defs.CheckResult:
    disk_with_rates = diskstat.compute_rates(disk=disk, value_store=value_store, this_time=now)
    yield from diskstat.check_diskstat_dict(
        params=params,
        disk=disk_with_rates,
        value_store=value_store,
        this_time=now,
    )


def _check_diskstat_io(
    item: str,
    params: Mapping[str, Any],
    section: diskstat.Section,
    value_store: MutableMapping[str, Any],
    now: float,
) -> type_defs.CheckResult:
    if item == "SUMMARY":
        disk = diskstat.summarize_disks(section.items())
    else:
        try:
            disk = section[item]
        except KeyError:
            return
    yield from _check_disk(params, disk, value_store, now)


def check_diskstat_io(
    item: str,
    params: Mapping[str, Any],
    section: diskstat.Section,
) -> type_defs.CheckResult:
    yield from _check_diskstat_io(item, params, section, get_value_store(), time.time())


def _cluster_check_diskstat_io(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Optional[diskstat.Section]],
    value_store: MutableMapping[str, Any],
    now: float,
) -> type_defs.CheckResult:
    present_sections = [section for section in section.values() if section is not None]
    if item == "SUMMARY":
        disk = diskstat.summarize_disks(
            item for node_section in present_sections for item in node_section.items()
        )
    else:
        disk = diskstat.combine_disks(
            node_section[item] for node_section in present_sections if item in node_section
        )
    yield from _check_disk(params, disk, value_store, now)


def cluster_check_diskstat_io(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Optional[diskstat.Section]],
) -> type_defs.CheckResult:
    yield from _cluster_check_diskstat_io(item, params, section, get_value_store(), time.time())


register.check_plugin(
    name="diskstat_io",
    service_name="Disk IO %s",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={"summary": True},
    discovery_ruleset_name="diskstat_inventory",
    discovery_function=diskstat.discovery_diskstat_generic,
    check_ruleset_name="diskstat",
    check_default_parameters={},
    check_function=check_diskstat_io,
    cluster_check_function=cluster_check_diskstat_io,
)


# We have to have more than one plugin.
# The the "SUMMARY" would start summarizing things that must not be mixed otherwise.
register.check_plugin(
    name="diskstat_io_volumes",
    service_name="Disk IO Volumes %s",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={"summary": True},
    discovery_ruleset_name="diskstat_inventory",
    discovery_function=diskstat.discovery_diskstat_generic,
    check_ruleset_name="diskstat",
    check_default_parameters={},
    check_function=check_diskstat_io,
    cluster_check_function=cluster_check_diskstat_io,
)


register.check_plugin(
    name="diskstat_io_director",
    service_name="Disk IO Director %s",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={"summary": True},
    discovery_ruleset_name="diskstat_inventory",
    discovery_function=diskstat.discovery_diskstat_generic,
    check_ruleset_name="diskstat",
    check_default_parameters={},
    check_function=check_diskstat_io,
)


# Consider reorganizing the special agent. We only need this extra check,
# because the disk info is buried in the poorly parsed section, and we have to
# "re-parse" it.
def check_hp_msa_io(
    item: str, params: Mapping[str, Any], section: hp_msa.Section
) -> type_defs.CheckResult:
    new_section = {}
    for name, values in section.items():
        try:
            new_section[name] = {
                "read_throughput": float(values["data-read-numeric"]),
                "write_throughput": float(values["data-written-numeric"]),
            }
        except (KeyError, ValueError):
            pass
    yield from check_diskstat_io(item, params, new_section)


register.check_plugin(
    name="hp_msa_disk_io",
    service_name="Disk IO %s",
    sections=["hp_msa_disk"],
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={"summary": True},
    discovery_ruleset_name="diskstat_inventory",
    discovery_function=diskstat.discovery_diskstat_generic,
    check_ruleset_name="diskstat",
    check_default_parameters={},
    check_function=check_hp_msa_io,
)


register.check_plugin(
    name="hp_msa_controller_io",
    service_name="Controller IO %s",
    sections=["hp_msa_controller"],
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={"summary": True},
    discovery_ruleset_name="diskstat_inventory",
    discovery_function=diskstat.discovery_diskstat_generic,
    check_ruleset_name="diskstat",
    check_default_parameters={},
    check_function=check_hp_msa_io,
)


def check_hp_msa_volume_io(
    item: str, params: Mapping[str, Any], section: hp_msa.Section
) -> type_defs.CheckResult:
    if item != "SUMMARY":
        if disk := section.get(item):
            yield Result(
                state=State.OK,
                summary=f"{disk['virtual-disk-name']} ({disk['raidtype']})",
            )
        return

    new_section = {}
    for name, values in section.items():
        try:
            new_section[name] = {
                "read_throughput": float(values["data-read-numeric"]),
                "write_throughput": float(values["data-written-numeric"]),
            }
        except (KeyError, ValueError):
            pass
    yield from check_diskstat_io("SUMMARY", params, new_section)


register.check_plugin(
    name="hp_msa_volume_io",
    service_name="Volume IO %s",
    sections=["hp_msa_volume"],
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={"summary": True},
    discovery_ruleset_name="diskstat_inventory",
    discovery_function=diskstat.discovery_diskstat_generic,
    check_ruleset_name="diskstat",
    check_default_parameters={},
    check_function=check_hp_msa_volume_io,
)
