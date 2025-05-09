#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from typing import Any, NamedTuple

from cmk.plugins.lib.diskstat import (
    check_diskstat_dict,
    combine_disks,
    discovery_diskstat_generic,
)
from cmk.plugins.lib.esx_vsphere import (
    average_parsed_data,
    CounterValues,
    SectionCounter,
)

from .agent_based_api.v1 import get_value_store, register, Result, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

# Example output:
# <<<esx_vsphere_counters:sep(124)>>>
# datastore.read|4c4ece34-3d60f64f-1584-0022194fe902|0#1#2|kiloBytesPerSecond
# datastore.read|4c4ece5b-f1461510-2932-0022194fe902|0#4#5|kiloBytesPerSecond
# datastore.numberReadAveraged|511e4e86-1c009d48-19d2-bc305bf54b07|0#0#0|number
# datastore.numberWriteAveraged|4c4ece34-3d60f64f-1584-0022194fe902|0#0#1|number
# datastore.totalReadLatency|511e4e86-1c009d48-19d2-bc305bf54b07|0#5#5|millisecond
# datastore.totalWriteLatency|4c4ece34-3d60f64f-1584-0022194fe902|0#2#7|millisecond


class PostParser(NamedTuple):
    key: str
    evaluate: Callable[[CounterValues], float]
    counter: str


_POST_PARSERS = [
    PostParser(
        key="read_throughput",
        evaluate=lambda x: int(average_parsed_data(x)) * 1024,
        counter="read",
    ),
    PostParser(
        key="write_throughput",
        evaluate=lambda x: int(average_parsed_data(x)) * 1024,
        counter="write",
    ),
    PostParser(
        key="read_ios",
        evaluate=lambda x: int(average_parsed_data(x)),
        counter="datastoreReadIops",
    ),
    PostParser(
        key="write_ios",
        evaluate=lambda x: int(average_parsed_data(x)),
        counter="datastoreWriteIops",
    ),
    PostParser(
        key="read_latency",
        evaluate=lambda x: max(map(int, x)) * 1e-3,
        counter="totalReadLatency",
    ),
    PostParser(
        key="write_latency",
        evaluate=lambda x: max(map(int, x)) * 1e-3,
        counter="totalWriteLatency",
    ),
    PostParser(
        key="latency",
        evaluate=lambda x: max(map(int, x)) * 1e-6,
        counter="sizeNormalizedDatastoreLatency",
    ),
]


def _get_item_mapping(section: SectionCounter) -> Mapping[str, str]:
    """datastores are either shown by human readable name (if available) or by the uuid"""
    map_instance_to_item = {}
    for parser in _POST_PARSERS:
        for instance in section.get(f"datastore.{parser.counter}", {}):
            map_instance_to_item[instance] = instance

    for instance, values in section.get("datastore.name", {}).items():
        if instance in map_instance_to_item and values[0][0] != "":
            map_instance_to_item[instance] = values[0][0][-1].replace(" ", "_")
    return map_instance_to_item


def discover_esx_vsphere_datastore_io(
    params: Sequence[Mapping[str, Any]],
    section: SectionCounter,
) -> DiscoveryResult:
    yield from discovery_diskstat_generic(
        params,
        _get_item_mapping(section).values(),
    )


def check_esx_vsphere_datastore_io(
    item: str,
    params: Mapping[str, Any],
    section: SectionCounter,
) -> CheckResult:
    yield from _check_esx_vsphere_datastore_io(
        item=item,
        params=params,
        section=section,
        now=time.time(),
        value_store=get_value_store(),
    )


def _check_esx_vsphere_datastore_io(
    item: str,
    params: Mapping[str, Any],
    section: SectionCounter,
    now: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if "datastore.read" not in section:
        return

    item_mapping = _get_item_mapping(section)

    datastores: dict[str, dict[str, float]] = {}
    for parser in _POST_PARSERS:
        field_data = section.get(f"datastore.{parser.counter}", {})

        for instance, values in field_data.items():
            item_name = item_mapping[instance]
            datastores.setdefault(item_name, {})[parser.key] = parser.evaluate(values[0][0])

    if item == "SUMMARY":
        # Exclude disks with only negative values. This means that no data could be collected by
        # the ESX host or vCenter.
        # See: https://github.com/vmware/pyvmomi/issues/191#issuecomment-72217028
        disk = combine_disks(
            (disk for disk in datastores.values() if all(x >= 0 for x in disk.values()))
        )
    else:
        try:
            disk = datastores[item]
        except KeyError:
            return

    if all(x < 0 for x in disk.values()):
        # A "-1" in the raw data indicates that the ESX host or vCenter could not determine a value.
        # See: https://github.com/vmware/pyvmomi/issues/191#issuecomment-72217028
        yield Result(state=State.UNKNOWN, summary="No valid data from queried host")
        return

    yield from check_diskstat_dict(
        params=params,
        disk=disk,
        value_store=value_store,
        this_time=now,
    )


register.check_plugin(
    name="esx_vsphere_datastore_io",
    service_name="Datastore IO %s",
    sections=["esx_vsphere_counters"],
    discovery_function=discover_esx_vsphere_datastore_io,
    discovery_ruleset_name="diskstat_inventory",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={"summary": True},
    check_function=check_esx_vsphere_datastore_io,
    check_default_parameters={},
    check_ruleset_name="diskstat",
)
