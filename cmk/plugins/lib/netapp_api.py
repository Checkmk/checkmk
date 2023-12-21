#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from typing import Any, Literal

from typing_extensions import TypedDict

from cmk.agent_based.v2 import get_rate, GetRateError, Metric, render, Result, Service, State
from cmk.agent_based.v2.type_defs import CheckResult, DiscoveryResult, StringTable
from cmk.plugins.lib.df import df_check_filesystem_single

CPUSection = TypedDict(
    "CPUSection",
    {
        "clustermode": dict[str, dict[str, str]],
        "7mode": dict[str, str],
    },
    total=False,
)

Instance = dict[str, str]
SectionMultipleInstances = dict[str, list[Instance]]
SectionSingleInstance = Mapping[str, Instance]
CustomKeys = Sequence[str] | None
ItemFunc = Callable[[str, Instance], str] | None


_DEV_KEYS = {
    "fan": ("cooling-element-is-error", "cooling-element-number"),
    "power supply unit": ("power-supply-is-error", "power-supply-element-number"),
}


def parse_netapp_api_multiple_instances(
    string_table: StringTable,
    custom_keys: CustomKeys = None,
    item_func: ItemFunc = None,
) -> SectionMultipleInstances:
    """
    >>> from pprint import pprint
    >>> pprint(parse_netapp_api_multiple_instances([
    ... ['interface e0a', 'mediatype auto-1000t-fd-up', 'flowcontrol full', 'mtusize 9000',
    ...  'ipspace-name default-ipspace', 'mac-address 01:b0:89:22:df:01'],
    ... ['interface e0a', 'mediatype auto-1000t-fd-up', 'flowcontrol full', 'mtusize 9000',
    ...  'ipspace-name default-ipspace', 'mac-address 01:b0:89:22:df:01'],
    ... ['interface ifgrp_sto', 'v4-primary-address.ip-address-info.address 11.12.121.33',
    ...  'v4-primary-address.ip-address-info.addr-family af-inet', 'mtusize 9000',
    ...  'v4-primary-address.ip-address-info.netmask-or-prefix 255.255.255.220',
    ...  'v4-primary-address.ip-address-info.broadcast 12.13.142.33', 'ipspace-name default-ipspace',
    ...  'mac-address 01:b0:89:22:df:01', 'v4-primary-address.ip-address-info.creator vfiler:vfiler0',
    ...  'send_mcasts 1360660', 'recv_errors 0', 'instance_name ifgrp_sto', 'send_errors 0',
    ...  'send_data 323931282332034', 'recv_mcasts 1234567', 'v4-primary-address.ip-address-info.address 11.12.121.21',
    ...  'v4-primary-address.ip-address-info.addr-family af-inet', 'v4-primary-address.ip-address-info.netmask-or-prefix 255.255.253.0',
    ...  'v4-primary-address.ip-address-info.broadcast 14.11.123.255', 'ipspace-name default-ipspace',
    ...  'mac-address 01:b0:89:22:df:02', 'v4-primary-address.ip-address-info.creator vfiler:vfiler0',
    ...  'send_mcasts 166092', 'recv_errors 0', 'instance_name ifgrp_srv-600', 'send_errors 0',
    ...  'send_data 12367443455534', 'recv_mcasts 2308439', 'recv_data 412332323639'],
    ... ]))
    {'e0a': [{'flowcontrol': 'full',
              'interface': 'e0a',
              'ipspace-name': 'default-ipspace',
              'mac-address': '01:b0:89:22:df:01',
              'mediatype': 'auto-1000t-fd-up',
              'mtusize': '9000'},
             {'flowcontrol': 'full',
              'interface': 'e0a',
              'ipspace-name': 'default-ipspace',
              'mac-address': '01:b0:89:22:df:01',
              'mediatype': 'auto-1000t-fd-up',
              'mtusize': '9000'}],
     'ifgrp_sto': [{'instance_name': 'ifgrp_srv-600',
                    'interface': 'ifgrp_sto',
                    'ipspace-name': 'default-ipspace',
                    'mac-address': '01:b0:89:22:df:02',
                    'mtusize': '9000',
                    'recv_data': '412332323639',
                    'recv_errors': '0',
                    'recv_mcasts': '2308439',
                    'send_data': '12367443455534',
                    'send_errors': '0',
                    'send_mcasts': '166092',
                    'v4-primary-address.ip-address-info.addr-family': 'af-inet',
                    'v4-primary-address.ip-address-info.address': '11.12.121.21',
                    'v4-primary-address.ip-address-info.broadcast': '14.11.123.255',
                    'v4-primary-address.ip-address-info.creator': 'vfiler:vfiler0',
                    'v4-primary-address.ip-address-info.netmask-or-prefix': '255.255.253.0'}]}
    """
    if custom_keys is None:
        custom_keys = []

    instances: SectionMultipleInstances = {}
    for line in string_table:
        instance = {}
        if len(line) < 2:
            continue
        name = line[0].split(" ", 1)[1]
        for element in line:
            tokens = element.split(" ", 1)
            instance[tokens[0]] = tokens[1]

        if custom_keys:
            custom_name = []
            for key in custom_keys:
                if key in instance:
                    custom_name.append(instance[key])
            name = ".".join(custom_name)

        if item_func:
            name = item_func(name, instance)

        instances.setdefault(name, [])
        instances[name].append(instance)

    return instances


def parse_netapp_api_single_instance(
    string_table: StringTable,
    custom_keys: CustomKeys = None,
    item_func: ItemFunc = None,
) -> SectionSingleInstance:
    """
    >>> from pprint import pprint
    >>> pprint(parse_netapp_api_single_instance([
    ... ['interface e0a', 'mediatype auto-1000t-fd-up', 'flowcontrol full', 'mtusize 9000',
    ...  'ipspace-name default-ipspace', 'mac-address 01:b0:89:22:df:01'],
    ... ['interface e0a', 'v4-primary-address.ip-address-info.address 11.12.121.33',
    ...  'v4-primary-address.ip-address-info.addr-family af-inet', 'mtusize 9000',
    ...  'v4-primary-address.ip-address-info.netmask-or-prefix 255.255.255.220',
    ...  'v4-primary-address.ip-address-info.broadcast 12.13.142.33', 'ipspace-name default-ipspace',
    ...  'mac-address 01:b0:89:22:df:01', 'v4-primary-address.ip-address-info.creator vfiler:vfiler0',
    ...  'send_mcasts 1360660', 'recv_errors 0', 'instance_name ifgrp_sto', 'send_errors 0',
    ...  'send_data 323931282332034', 'recv_mcasts 1234567', 'v4-primary-address.ip-address-info.address 11.12.121.21',
    ...  'v4-primary-address.ip-address-info.addr-family af-inet', 'v4-primary-address.ip-address-info.netmask-or-prefix 255.255.253.0',
    ...  'v4-primary-address.ip-address-info.broadcast 14.11.123.255', 'ipspace-name default-ipspace',
    ...  'mac-address 01:b0:89:22:df:02', 'v4-primary-address.ip-address-info.creator vfiler:vfiler0',
    ...  'send_mcasts 166092', 'recv_errors 0', 'instance_name ifgrp_srv-600', 'send_errors 0',
    ...  'send_data 12367443455534', 'recv_mcasts 2308439', 'recv_data 412332323639'],
    ... ]))
    {'e0a': {'flowcontrol': 'full',
             'interface': 'e0a',
             'ipspace-name': 'default-ipspace',
             'mac-address': '01:b0:89:22:df:01',
             'mediatype': 'auto-1000t-fd-up',
             'mtusize': '9000'}}
    """
    return {
        key: instances[0]
        for key, instances in parse_netapp_api_multiple_instances(
            string_table,
            custom_keys=custom_keys,
            item_func=item_func,
        ).items()
    }


def _single_configured(params: Mapping[str, Any]) -> bool:
    return params["mode"] == "single"


def discover_single(params: Mapping[str, Any], section: SectionSingleInstance) -> DiscoveryResult:
    if not _single_configured(params):
        return
    yield from (Service(item=item) for item in section)


def discover_summary(
    params: Mapping[str, Any],
    section: SectionSingleInstance,
) -> DiscoveryResult:
    if not section or _single_configured(params):
        return
    yield Service(item="Summary")


def get_single_check(
    device_type: Literal["fan", "power supply unit"]
) -> Callable[[str, SectionSingleInstance], CheckResult]:
    error_key, number_key = _DEV_KEYS[device_type]

    def check_single(
        item: str,
        section: SectionSingleInstance,
    ) -> CheckResult:
        if not (device := section.get(item)):
            return

        if device[error_key] == "true":
            yield Result(
                state=State.CRIT,
                summary=f"Error in {device_type} {device[number_key]}",
            )
        else:
            yield Result(state=State.OK, summary="Operational state OK")

    return check_single


def _pluralize(thing: str, count: int) -> str:
    return thing if count == 1 else f"{thing}s"


def get_summary_check(
    device_type: Literal["fan", "power supply unit"]
) -> Callable[[str, SectionSingleInstance], CheckResult]:
    error_key, _number_key = _DEV_KEYS[device_type]

    def check_summary(
        item: str,
        section: SectionSingleInstance,
    ) -> CheckResult:
        total = len(section)
        erred = [k for k, v in section.items() if v.get(error_key) == "true"]
        ok_count = total - len(erred)

        yield Result(state=State.OK, summary=f"OK: {ok_count} of {total}")

        if erred:
            yield Result(
                state=State.CRIT,
                summary=f"Failed: {len(erred)} ({', '.join(erred)})",
            )

    return check_summary


def single_volume_metrics(
    counter_names: Sequence[tuple[str, str, str]],
    counter_values: Mapping[str, float],
    value_store: MutableMapping[str, Any],
    time_now: float,
) -> Iterable[Metric]:
    def _create_key(protocol: str, mode: str, field: str) -> str:
        return "_".join([protocol, mode, field]) if protocol else "_".join([mode, field])

    base = {}
    metrics_map = {"write_ops": "write_ops_s"}

    for key in counter_names:
        protocol = key[0]
        mode = key[1]
        field = key[2]

        counter_name = _create_key(*key)

        if (counter_value := counter_values.get(counter_name)) is None:
            continue

        try:
            delta = get_rate(
                value_store, counter_name, time_now, counter_value, raise_overflow=True
            )
        except GetRateError:
            continue

        # Quite hacky.. this base information is used later on by the "latency" field
        if field == "ops":
            # the strip() is used to create a key like "...read_ops" or "...write_ops" (... is the "protocol")
            # those keys where "...read_ops" and "...write_ops" for the old netapp ontap api
            # and are "...total_read_ops", "...total_write_ops" for the new netapp rest api
            base[counter_name.replace("total_", "")] = 1.0 if delta == 0.0 else float(delta)

        if mode in ["read", "write"] and field == "latency":
            # See https://library.netapp.com/ecmdocs/ECMP1608437/html/GUID-04407796-688E-489D-901C-A6C9EAC2A7A2.html
            # for scaling issues:
            # read_latency           micro
            # write_latency          micro
            # other_latency          micro
            # nfs_read_latency       micro
            # nfs_write_latency      micro
            # nfs_other_latency      micro
            # cifs_read_latency      micro
            # cifs_write_latency     micro
            # cifs_other_latency     micro
            # san_read_latency       micro
            # san_write_latency      micro
            # san_other_latency      micro
            #
            # === 7-Mode environments only ===
            # fcp_read_latency       milli
            # fcp_write_latency      milli
            # fcp_other_latency      milli
            # iscsi_read_latency     milli
            # iscsi_write_latency    milli
            # iscsi_other_latency    milli
            #
            # FIXME The metric system expects milliseconds but should get seconds
            if protocol in ["fcp", "iscsi"]:
                divisor = 1.0
            else:
                divisor = 1000.0
            delta /= (
                divisor
                * base[
                    _create_key(
                        protocol,
                        mode,
                        "ops",
                    )
                ]
            )  # fixed: true-division
        yield Metric(metrics_map.get(counter_name, counter_name), delta)


def combine_netapp_api_volumes(
    volumes_in_group: list[str], section: Mapping[str, Mapping[str, int | str]]
) -> tuple[Mapping[str, float], Mapping[str, str]]:
    combined_volume: dict[str, Any] = {}
    volumes_not_online = {}

    for volume_name in volumes_in_group:
        volume = section[volume_name]

        state = str(volume.get("state"))
        if state != "online":
            volumes_not_online[volume_name] = state

        else:
            for k, v in volume.items():
                if isinstance(v, int):
                    combined_volume.setdefault(k, 0.0)
                    combined_volume[k] += v
                elif isinstance(v, str):
                    # if it is a string I keep a value just to be able to
                    # build a pydantic model when returned
                    combined_volume[k] = v

    n_vols_online = len(volumes_in_group) - len(volumes_not_online)
    if n_vols_online:
        for k, vs in combined_volume.items():
            if k.endswith("latency"):
                combined_volume[k] = float(vs) / n_vols_online

    return combined_volume, volumes_not_online


def check_netapp_luns(
    item: str,
    volume_name: str,
    server_name: str,
    online: bool,
    read_only: bool,
    size_total_bytes: int,
    size_total: float,
    size_available: float,
    now: float,
    value_store: MutableMapping[str, Any],
    params: Mapping[str, Any],
) -> CheckResult:
    yield Result(state=State.OK, summary=f"Volume: {volume_name}")
    yield Result(state=State.OK, summary=f"Vserver: {server_name}")

    if not online:
        yield Result(state=State.CRIT, summary="LUN is offline")

    if read_only != params.get("read_only"):
        expected = str(params.get("read_only")).lower()
        yield Result(
            state=State.WARN,
            summary=f"read-only is {str(read_only).lower()} (expected: {expected})",
        )

    if params.get("ignore_levels"):
        yield Result(state=State.OK, summary=f"Total size: {render.bytes(size_total_bytes)}")
        yield Result(state=State.OK, summary="Used space is ignored")
    else:
        yield from df_check_filesystem_single(
            value_store,
            item,
            size_total,
            size_available,
            0,
            None,
            None,
            params,
            this_time=now,
        )
