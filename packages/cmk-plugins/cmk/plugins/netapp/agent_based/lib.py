#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from typing import Any, Literal, NamedTuple, TypedDict

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    get_rate,
    GetRateError,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib import interfaces
from cmk.plugins.lib.df import df_check_filesystem_single
from cmk.plugins.netapp import models

Instance = dict[str, str]
SectionSingleInstance = Mapping[str, Instance]

DEV_KEYS = {
    "fan": ("cooling-element-is-error", "cooling-element-number"),
    "power supply unit": ("power-supply-is-error", "power-supply-element-number"),
}

MACList = list[tuple[str, str | None]]


class NICExtraInfo(TypedDict, total=False):
    grouped_if: MACList
    speed_differs: tuple[int, int]
    home_port: str
    home_node: str | None
    is_home: bool
    failover_ports: Sequence[Mapping[str, str]]
    failover_policy: str


ExtraInfo = Mapping[str, NICExtraInfo]
IfSection = tuple[interfaces.Section[interfaces.InterfaceWithCounters], ExtraInfo]

STATUS_MAP = {
    "check_and_crit": 2,
    "check_and_warn": 1,
    "check_and_display": 0,
}
INFO_INCLUDED_MAP = {"dont_show_and_check": False}

# rest failover policies are mapped different than
# cli failover policies. This maps translates from rest-terms to cli-terms
# for a better user experience
FAILOVER_REST_TRANSLATION = {
    "home_port_only": "disabled",
    "default": "system-defined",
    "home_node_only": "local-only",
    "sfo_partners_only": "sfo-partner-only",
    "broadcast_domain_only": "broadcast-domain-wide",
}

FAILOVER_STATUS = {
    "home_port_only": State.OK,
    "default": State.OK,
    "home_node_only": State.OK,
    "broadcast_domain_only": State.OK,
}


class Qtree(NamedTuple):
    quota: str
    quota_users: str
    volume: str
    disk_limit: str
    disk_used: str
    files_used: str = ""
    file_limit: str = ""


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
    device_type: Literal["fan", "power supply unit"],
) -> Callable[[str, SectionSingleInstance], CheckResult]:
    error_key, number_key = DEV_KEYS[device_type]

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


def get_summary_check(
    device_type: Literal["fan", "power supply unit"],
) -> Callable[[str, SectionSingleInstance], CheckResult]:
    error_key, _number_key = DEV_KEYS[device_type]

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
    online: bool,
    read_only: bool | None,
    size_total_bytes: int,
    size_total: float,
    size_available: float,
    now: float,
    value_store: MutableMapping[str, Any],
    params: Mapping[str, Any],
) -> CheckResult:
    if not online:
        yield Result(state=State.CRIT, summary="LUN is offline")

    if read_only != params.get("read_only"):
        expected = str(params.get("read_only")).lower()
        yield Result(
            state=State.WARN,
            summary=f"read-only is {str(read_only if read_only is not None else 'unknown').lower()} (expected: {expected})",
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


def merge_if_sections(
    interfaces_section: SectionSingleInstance,
    if_mac_list: MutableMapping[str, MACList],
    timestamp: float,
) -> IfSection:
    nics = []
    extra_info: dict[str, NICExtraInfo] = {}
    for idx, (nic_name, values) in enumerate(sorted(interfaces_section.items())):
        speed = values.get("speed", 0)

        # Try to determine the speed and state for virtual interfaces
        # We know all physical interfaces for this virtual device and use the highest available
        # speed as the virtual speed. Note: Depending on the configuration this behaviour might
        # differ, e.g. the speed of all interfaces might get accumulated..
        # Additionally, we check if not all interfaces of the virtual group share the same
        # connection speed
        if not speed:
            if "mac-address" in values:
                mac_list = if_mac_list[values["mac-address"]]
                if len(mac_list) > 1:  # check if this interface is grouped
                    extra_info.setdefault(nic_name, {})

                    max_speed = 0
                    min_speed = 1024**5
                    for tmp_if, _ in mac_list:
                        if tmp_if == nic_name or "speed" not in interfaces_section[tmp_if]:
                            continue
                        check_speed = int(interfaces_section[tmp_if]["speed"])
                        max_speed = max(max_speed, check_speed)
                        min_speed = min(min_speed, check_speed)
                    if max_speed != min_speed:
                        extra_info[nic_name]["speed_differs"] = (max_speed, min_speed)
                    speed = max_speed

        # Virtual interfaces is "Up" if at least one physical interface is up
        if "state" in values:
            oper_status = values["state"]
        else:
            oper_status = "2"
            if "mac-address" in values:
                for tmp_if, tmp_oper_status in if_mac_list[values["mac-address"]]:
                    if tmp_oper_status == "1":
                        oper_status = "1"
                        break

        if "failover_ports" in values and values["failover_ports"] != "none":
            extra_info.setdefault(nic_name, {})["failover_ports"] = [
                {
                    "node": node,
                    "port": name,
                    "link-status": link_status,
                }
                for port in values["failover_ports"].split(";")
                for node, name, link_status, *_ in (port.split("|"),)
            ]

        nics.append(
            interfaces.InterfaceWithCounters(
                interfaces.Attributes(
                    index=str(idx + 1),
                    descr=nic_name,
                    alias=values.get("interface-name", ""),
                    type="6",
                    speed=interfaces.saveint(speed),
                    oper_status=oper_status,
                    phys_address=interfaces.mac_address_from_hexstring(
                        values.get("mac-address", "")
                    ),
                    speed_as_text=speed == "auto" and "auto" or "",
                ),
                interfaces.Counters(
                    in_octets=interfaces.saveint(values.get("recv_data", 0)),
                    in_ucast=interfaces.saveint(values.get("recv_packet", 0)),
                    in_mcast=interfaces.saveint(values.get("recv_mcasts", 0)),
                    in_err=interfaces.saveint(values.get("recv_errors", 0)),
                    out_octets=interfaces.saveint(values.get("send_data", 0)),
                    out_ucast=interfaces.saveint(values.get("send_packet", 0)),
                    out_mcast=interfaces.saveint(values.get("send_mcasts", 0)),
                    out_err=interfaces.saveint(values.get("send_errors", 0)),
                ),
                timestamp,
            )
        )
        if "home-port" in values:
            extra_info.setdefault(nic_name, {}).update(
                {
                    "home_port": values["home-port"],
                    "home_node": values.get("home-node"),
                    "is_home": str(values.get("is-home")).lower() == "true",
                    "failover_policy": values["failover"],
                }
            )

    return nics, extra_info


def _check_netapp_interfaces(
    item: str,
    params: Mapping[str, Any],
    nics: interfaces.Section[interfaces.InterfaceWithCounters],
    extra_info: ExtraInfo,
) -> CheckResult:
    for iface in interfaces.matching_interfaces_for_item(item, nics):
        vif = extra_info.get(iface.attributes.descr)
        if vif is None:
            continue

        failover_policy = vif.get("failover_policy", "unknown")
        yield Result(
            state=FAILOVER_STATUS.get(failover_policy, State.UNKNOWN),
            summary=f"Failover policy: {FAILOVER_REST_TRANSLATION.get(failover_policy, failover_policy)}",
        )

        speed_state, speed_info_included = 1, True
        home_state, home_info_included = 0, True

        if "match_same_speed" in params:
            speed_behaviour = params["match_same_speed"]
            speed_info_included = INFO_INCLUDED_MAP.get(
                speed_behaviour,
                speed_info_included,
            )
            speed_state = STATUS_MAP.get(speed_behaviour, speed_state)

        if "home_port" in params:
            home_behaviour = params["home_port"]
            home_info_included = INFO_INCLUDED_MAP.get(home_behaviour, home_info_included)
            home_state = STATUS_MAP.get(home_behaviour, home_state)

        if "home_port" in vif and home_info_included:
            is_home_port = vif["is_home"]
            mon_state = 0 if is_home_port else home_state
            home_attribute = "is %shome port" % ("" if is_home_port else "not ")
            yield Result(
                state=State(mon_state),
                summary="Current Port: {} ({})".format(vif["home_port"], home_attribute),
            )

        if "failover_ports" in vif:
            failover_group_str = ", ".join(
                f"{fop['node']}:{fop['port']}={fop['link-status']}"
                for fop in sorted(vif["failover_ports"], key=lambda x: (x["node"], x["port"]))
            )
            yield Result(
                state=(
                    State.CRIT
                    if any(
                        fop["link-status"] != "up" and fop["node"] == vif["home_node"]
                        for fop in vif["failover_ports"]
                    )
                    else (
                        State.WARN
                        if any(fop["link-status"] != "up" for fop in vif["failover_ports"])
                        else State.OK
                    )
                ),
                notice=f"Failover Group: [{failover_group_str}]",
            )

        if "speed_differs" in vif and speed_info_included:
            yield Result(
                state=State(speed_state),
                summary="Interfaces do not have the same speed",
            )


def check_netapp_interfaces(
    item: str,
    params: Mapping[str, Any],
    section: IfSection,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    nics, extra_info = section
    yield from interfaces.check_multiple_interfaces(
        item,
        params,
        nics,
        value_store=value_store,
    )

    yield from _check_netapp_interfaces(
        item,
        params,
        nics,
        extra_info,
    )


def check_netapp_vs_traffic(
    item_counters: Mapping[str, int],
    protocol_name: str,
    protocol_map: Mapping,
    latency_calc_ref: Mapping,
    now: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    protoname, values = protocol_map.get(protocol_name, (None, None))
    if protoname is None or values is None:
        return None

    def get_ref(protocol: str, what: str, item_counters: Mapping[str, int]) -> int | None:
        # According to "NetApp® Unified Storage Performance Management",
        # latency calculation is a function of the number of ops.
        refname = latency_calc_ref.get(protocol, {}).get(what)
        try:
            return int(item_counters[refname])
        except KeyError:
            return None

    for what, perfname, perftext, scale, format_func in values:
        if what not in item_counters:
            continue

        ref = get_ref(protocol_name, what, item_counters)
        try:
            rate = get_rate(
                value_store,
                f"{protocol_name}.{what}",
                ref if ref is not None else now,
                int(item_counters[what]) * scale,
                raise_overflow=True,
            )
            yield Result(
                state=State.OK,
                summary=f"{protoname} {perftext}: {format_func(rate)}",
            )
            yield Metric(name=perfname, value=rate)
        except IgnoreResultsError:
            yield Result(state=State.OK, summary=f"{protoname} {perftext}: -")


def discover_netapp_qtree_quota(
    params: Mapping[str, Any], section: Mapping[str, Qtree]
) -> DiscoveryResult:
    def _get_item_names(qtree: Qtree) -> tuple[str, str]:
        short_name = ".".join([n for n in [qtree.quota, qtree.quota_users] if n])
        long_name = f"{qtree.volume}/{short_name}" if qtree.volume else short_name
        return short_name, long_name

    exclude_volume = params.get("exclude_volume", False)
    for name, qtree in section.items():
        if qtree.disk_limit.isdigit():
            short_name, long_name = _get_item_names(qtree)

            if (exclude_volume and name == short_name) or (
                not exclude_volume and name == long_name
            ):
                yield Service(item=name)


def check_netapp_qtree_quota(
    item_name: str,
    qtree: Qtree,
    params: Mapping[str, Any],
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    disk_limit = qtree.disk_limit

    if not disk_limit.isdigit():
        yield Result(state=State.UNKNOWN, summary="Qtree has no disk limit set")
        return

    if not qtree.disk_used.isdigit():
        yield Result(state=State.UNKNOWN, summary="Qtree has no used space data set")
        return

    size_total = int(disk_limit) / 1024**2
    size_avail = size_total - int(qtree.disk_used) / 1024**2
    if qtree.files_used.isdigit() and qtree.file_limit.isdigit():
        inodes_total = int(qtree.file_limit)
        inodes_avail = inodes_total - int(qtree.files_used)
    else:
        inodes_total = None
        inodes_avail = None

    yield from df_check_filesystem_single(
        value_store=value_store,
        mountpoint=item_name,
        filesystem_size=size_total,
        free_space=size_avail,
        reserved_space=0,
        inodes_total=inodes_total,
        inodes_avail=inodes_avail,
        params=params,
    )


def filter_metrocluster_items(
    section_netapp_ontap_volumes: Mapping[str, models.VolumeModel],
    section_netapp_ontap_vs_status: Mapping[str, models.SvmModel],
) -> Mapping[str, models.VolumeModel]:
    """
    As per SUP-22707 and SUP-22904
    volumes and snapshots of SVMs of subtype "sync_destination" (metrocluster)
    should not be discovered.
    """
    return {
        volume_id: volume
        for volume_id, volume in section_netapp_ontap_volumes.items()
        if (svm := section_netapp_ontap_vs_status.get(volume.svm_name))
        and svm.subtype != "sync_destination"
    }
