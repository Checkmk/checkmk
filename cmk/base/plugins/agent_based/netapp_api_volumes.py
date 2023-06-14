#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_rate,
    get_value_store,
    GetRateError,
    Metric,
    register,
    Result,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.df import (
    df_check_filesystem_single,
    df_discovery,
    FILESYSTEM_DEFAULT_LEVELS,
    INODES_DEFAULT_PARAMS,
    MAGIC_FACTOR_DEFAULT_PARAMS,
    mountpoints_in_group,
    TREND_DEFAULT_PARAMS,
)

Section = Mapping[str, Mapping[str, int | str]]

# <<<netapp_api_volumes:sep(9)>>>
# volume vol0 size-available 556613632    state online    files-total 25876   files-used 8646 size-total 848203776    fcp_write_data 0    fcp_read_data 0cifs_write_data 0    iscsi_read_latency 0    iscsi_write_data 0  read_data 201265528798  nfs_write_latency 977623886 san_write_latency 0 san_write_data 0read_latency 1529821621 cifs_read_latency 0 fcp_write_latency 0 fcp_read_latency 0  iscsi_write_latency 0   nfs_read_latency 1491050012 iscsi_read_data 0   instance_name vol0  cifs_read_data 0    nfs_read_data 197072260981  write_latency 1528780977    san_read_data 0 san_read_latency 0  write_data 13926719804  nfs_write_data 2789744628   cifs_write_latency 0


def parse_netapp_api_volumes(string_table: StringTable) -> Section:
    volumes = {}
    for line in string_table:
        volume: dict[str, int | str] = {}
        name = line[0].split(" ", 1)[1]
        for element in line[1:]:
            key, val = element.split(" ", 1)
            try:
                volume[key] = int(val)
            except ValueError:
                volume[key] = val

        # Clustermode specific
        if "vserver_name" in volume:
            name = "%s.%s" % (volume["vserver_name"], volume["name"])

        volumes[name] = volume

    return volumes


register.agent_section(
    name="netapp_api_volumes",
    parse_function=parse_netapp_api_volumes,
)


def discover_netapp_api_volumes(
    params: Sequence[Mapping[str, Any]], section: Section
) -> DiscoveryResult:
    yield from df_discovery(params, section)


def _create_key(protocol: str, mode: str, field: str) -> str:
    if protocol:
        return "_".join([protocol, mode, field])
    return "_".join([mode, field])


def _check_single_netapp_api_volume(  # type: ignore[no-untyped-def]
    item: str, params: Mapping[str, Any], volume
) -> CheckResult:
    value_store = get_value_store()
    mega = 1024.0 * 1024.0
    inodes_total = volume["files-total"]
    yield from df_check_filesystem_single(
        value_store,
        item,
        volume["size-total"] / mega,
        volume["size-available"] / mega,
        0,
        inodes_total,
        inodes_total - volume["files-used"],
        params,
    )

    yield from _generate_volume_metrics(value_store, params, volume)
    if volume.get("is-space-enforcement-logical") == "false":
        logical_used = volume["logical-used"]
        size_total = volume["size-total"]
        logical_available = size_total - logical_used
        yield Metric(
            name="logical_used",
            value=logical_used,
            boundaries=(0.0, volume["size-total"]),
        )
        yield Metric(
            name="space_savings",
            value=volume["size-available"] - logical_available,
            boundaries=(0.0, volume["size-total"]),
        )


def _generate_volume_metrics(
    value_store: MutableMapping[str, Any],
    params: Mapping[str, Any],
    volume: Mapping[str, float],
) -> Iterable[Metric]:
    now = time.time()
    base = {}
    metrics_map = {"write_ops": "write_ops_s"}

    for protocol in params.get("perfdata", []):
        for mode in ["read", "write", "other"]:
            for field in ["data", "ops", "latency"]:
                key = _create_key(protocol, mode, field)
                value = volume.get(key)
                if value is None:
                    continue

                try:
                    delta = get_rate(value_store, key, now, value, raise_overflow=True)
                except GetRateError:
                    continue

                # Quite hacky.. this base information is used later on by the "latency" field
                if field == "ops":
                    if delta == 0.0:
                        base[key] = 1.0
                    else:
                        base[key] = float(delta)

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

                yield Metric(metrics_map.get(key, key), delta)


def _combine_netapp_api_volumes(
    volumes_in_group: list[str], section: Section
) -> tuple[Mapping[str, float], Mapping[str, str]]:
    combined_volume: dict[str, float] = {}
    volumes_not_online = {}

    for volume_name in volumes_in_group:
        volume = section[volume_name]

        state = str(volume.get("state"))
        if volume.get("state") != "online":
            volumes_not_online[volume_name] = state

        else:
            for k, v in volume.items():
                if isinstance(v, int):
                    combined_volume.setdefault(k, 0.0)
                    combined_volume[k] += v

    n_vols_online = len(volumes_in_group) - len(volumes_not_online)
    if n_vols_online:
        for k, vs in combined_volume.items():
            if k.endswith("latency"):
                combined_volume[k] = float(vs) / n_vols_online

    return combined_volume, volumes_not_online


# Cannot use decorator get_parsed_item_data for this check function due to the
# specific error message for legacy checks with a UUID as item
def check_netapp_api_volumes(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if "patterns" in params:
        volumes_in_group = mountpoints_in_group(section, *params["patterns"])
        if not volumes_in_group:
            yield Result(
                state=State.UNKNOWN,
                summary="No volumes matching the patterns of this group",
            )
            return

        combined_volumes, volumes_not_online = _combine_netapp_api_volumes(
            volumes_in_group,
            section,
        )

        for vol, state in volumes_not_online.items():
            yield Result(state=State.WARN, summary="Volume %s is %s" % (vol, state))

        if combined_volumes:
            yield from _check_single_netapp_api_volume(item, params, combined_volumes)

            yield Result(state=State.OK, notice="%d volume(s) in group" % len(volumes_in_group))

        return

    volume = section.get(item)

    if not volume:
        if item.count("-") >= 4:
            yield Result(
                state=State.UNKNOWN,
                summary="Service description with UUID is no longer supported. Please rediscover.",
            )
        return

    if volume.get("state") != "online":
        yield Result(state=State.WARN, summary="Volume is %s" % volume.get("state"))
        return

    yield from _check_single_netapp_api_volume(item, params, volume)


register.check_plugin(
    name="netapp_api_volumes",
    service_name="Volume %s",
    discovery_function=discover_netapp_api_volumes,
    discovery_default_parameters={"groups": []},
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=register.RuleSetType.ALL,
    check_function=check_netapp_api_volumes,
    check_default_parameters={
        **FILESYSTEM_DEFAULT_LEVELS,
        **MAGIC_FACTOR_DEFAULT_PARAMS,
        **INODES_DEFAULT_PARAMS,
        **TREND_DEFAULT_PARAMS,
    },
    check_ruleset_name="netapp_volumes",
)
