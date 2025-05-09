#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    RuleSetType,
)
from cmk.plugins.lib.diskstat import (
    check_diskstat_dict_legacy,
    combine_disks,
    discovery_diskstat_generic,
    DISKSTAT_DEFAULT_PARAMS,
)
from cmk.plugins.vsphere.lib.esx_vsphere import average_parsed_data, CounterValues, SectionCounter

# Example output:
# <<<esx_vsphere_counters:sep(124)>>>
# datastore.read|4c4ece34-3d60f64f-1584-0022194fe902|0#1#2|kiloBytesPerSecond
# datastore.read|4c4ece5b-f1461510-2932-0022194fe902|0#4#5|kiloBytesPerSecond
# datastore.numberReadAveraged|511e4e86-1c009d48-19d2-bc305bf54b07|0#0#0|number
# datastore.numberWriteAveraged|4c4ece34-3d60f64f-1584-0022194fe902|0#0#1|number
# datastore.totalReadLatency|511e4e86-1c009d48-19d2-bc305bf54b07|0#5#5|millisecond
# datastore.totalWriteLatency|4c4ece34-3d60f64f-1584-0022194fe902|0#2#7|millisecond


@dataclass(frozen=True)
class PostParser:
    # Based on a chat with ChatGPT and a search on Perplexity.ai:
    # In VMware vSphere metrics, a value of -1 typically indicates that the metric data is unavailable,
    # not applicable, or not collected for that particular interval or object.

    _RAW_INVALID_VALUE: ClassVar[str] = "-1"

    key: str
    evaluate: Callable[[CounterValues], float]
    counter: str

    def __call__(self, values: CounterValues) -> float | None:
        valid_values = [value for value in values if value != self._RAW_INVALID_VALUE]
        return self.evaluate(valid_values) if any(valid_values) else None


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
            if (parsed_value := parser(values[0][0])) is not None:
                datastores.setdefault(item_name, {})[parser.key] = parsed_value

    if item == "SUMMARY":
        disk = combine_disks(datastores.values())
    else:
        try:
            disk = datastores[item]
        except KeyError:
            return

    yield from check_diskstat_dict_legacy(
        params=params,
        disk=disk,
        value_store=value_store,
        this_time=now,
    )


check_plugin_esx_vsphere_datastore_io = CheckPlugin(
    name="esx_vsphere_datastore_io",
    service_name="Datastore IO %s",
    sections=["esx_vsphere_counters"],
    discovery_function=discover_esx_vsphere_datastore_io,
    discovery_ruleset_name="diskstat_inventory",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=DISKSTAT_DEFAULT_PARAMS,
    check_function=check_esx_vsphere_datastore_io,
    check_default_parameters={},
    check_ruleset_name="diskstat",
)
