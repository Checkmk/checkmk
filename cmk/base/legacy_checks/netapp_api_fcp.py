#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.netapp_api import (
    get_and_try_cast_to_int,
    netapp_api_parse_lines,
)
from cmk.base.config import check_info

from cmk.agent_based.v2 import get_rate, get_value_store, IgnoreResultsError, render
from cmk.plugins.lib.interfaces import bandwidth_levels, BandwidthUnit, PredictiveLevels

# <<<netapp_api_fcp:sep(9)>>>
# fcp 50:0a:09:84:80:91:96:6e sfp-wavelength 850  fabric-name 10:00:50:eb:1a:b8:68:46 speed auto  port-address 65536  sfp-tx-power 425.7 (uWatts) sfp-part-number AFBR-57F5MZ-NA1 hardware-rev 2  is-sfp-tx-power-in-range true   state online    sfp-connector LC    sfp-formfactor SFP  sfp-encoding 64B66B connection-established ptp  sfp-fc-speedcapabilities 4,8,16 (Gbit/sec)  node TESTSYS01-01 sfp-date-code 15:04:17  is-sfp-rx-power-in-range true   media-type ptp  node-name 50:0a:09:80:80:91:96:6e   sfp-rev 01  sfp-rx-power 423.6 (uWatts) sfp-vendor-oui 0:23:106 switch-port sansw1:0    physical-protocol fibre_channel data-link-rate 8    firmware-rev 7.4.0  adapter 0e  sfp-vendor-name AVAGO   fabric-established true is-sfp-optical-transceiver-valid true   info-name Fibre Channel Target Adapter 0e (QLogic 8324 (8362), rev. 2, 16G) max-speed 16    sfp-serial-number AC1516J01XD   is-sfp-diagnostics-internally-calibrated true   recverr_crc 0   recverr_disparity 0 portlogout_notinloopmap 0   read_ops 0  avg_write_latency 0 write_size_hist 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 portcfg_portid_change 0 read_size_hist 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0  ctio_nocontext 0    total_inot 221  other_ops 0 port_name port.0e   tprlo 0 avg_latency 0   login_affecting_tprlo 0 node_name TESTSYS01-01    login_affecting_pdisc 0 write_latency_hist 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0  login_affecting_logo 0  recverr_bad_eof 0   ls_reject 0 portlogout_ownopn_rxed 0    avg_read_latency 0  link_failure 0  portlogout_conflicting_adisc 0  invalid_crc 0   portlogout_disc_rjt 0   portlogout_disc_timeout 0   disparity_error 0   login_affecting_adisc 0 portlogout_unexp_adisc_resp 0   portcfg_bad_fan 0   portlogout_login_req 0  discared_frames 0   portlogout_transmit_failed 0    total_ops 0 recv_err 0  write_ops 0 invalid_transmission_word 0 recverr_bad_sof 0   login_affecting_plogi 0 write_data 0    read_latency_hist 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0   inits_connected 0   total_logouts 0 invalid_inot 0  port_id port.0e bad_sof 0   instance_uuid 50:0a:09:84:80:91:96:6e   read_data 0 node_uuid 129e1f94-5bab-11e5-9e99-07c86cc5b5aa  bad_eof 0   ctio_nohandle 0 portcfg_toplogy_change 0    avg_other_latency 0 instance_name port.0e   port_wwpn 50:0a:09:84:80:91:96:6e   ctio_noispexch 0    portcfg_flogi_rjt 0 dropped_atio 0  portlogout_abts_timeout 0   portcfg_flogi_timeout 0 recverr_framelen 0  login_affecting_prlo 0  total_logins 0  login_affecting_prli 0  portcfg_flogi_acc 0 frame_length_error 0
# fcp 50:0a:09:83:80:91:96:6e sfp-wavelength 850  fabric-name 10:00:50:eb:1a:b8:78:01 speed auto  port-address 65536  sfp-tx-power 419.3 (uWatts) sfp-part-number AFBR-57F5MZ-NA1 hardware-rev 2  is-sfp-tx-power-in-range true   state online    sfp-connector LC    sfp-formfactor SFP  sfp-encoding 64B66B connection-established ptp  sfp-fc-speedcapabilities 4,8,16 (Gbit/sec)  node TESTSYS01-01 sfp-date-code 15:04:17  is-sfp-rx-power-in-range true   media-type ptp  node-name 50:0a:09:80:80:91:96:6e   sfp-rev 01  sfp-rx-power 374.7 (uWatts) sfp-vendor-oui 0:23:106 switch-port sansw2:0    physical-protocol fibre_channel data-link-rate 8    firmware-rev 7.4.0  adapter 0f  sfp-vendor-name AVAGO   fabric-established true is-sfp-optical-transceiver-valid true   info-name Fibre Channel Target Adapter 0f (QLogic 8324 (8362), rev. 2, 16G) max-speed 16    sfp-serial-number AC1516J01XB   is-sfp-diagnostics-internally-calibrated true   recverr_crc 0   recverr_disparity 0 portlogout_notinloopmap 0   read_ops 0  avg_write_latency 0 write_size_hist 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 portcfg_portid_change 0 read_size_hist 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0  ctio_nocontext 0    total_inot 206  other_ops 0 port_name port.0f   tprlo 0 avg_latency 0   login_affecting_tprlo 0 node_name TESTSYS01-01    login_affecting_pdisc 0 write_latency_hist 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0  login_affecting_logo 0  recverr_bad_eof 0   ls_reject 0 portlogout_ownopn_rxed 0    avg_read_latency 0  link_failure 0  portlogout_conflicting_adisc 0  invalid_crc 0   portlogout_disc_rjt 0   portlogout_disc_timeout 0   disparity_error 0   login_affecting_adisc 0 portlogout_unexp_adisc_resp 0   portcfg_bad_fan 0   portlogout_login_req 0  discared_frames 0   portlogout_transmit_failed 0    total_ops 0 recv_err 0  write_ops 0 invalid_transmission_word 0 recverr_bad_sof 0   login_affecting_plogi 0 write_data 0    read_latency_hist 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0   inits_connected 0   total_logouts 0 invalid_inot 0  port_id port.0f bad_sof 0   instance_uuid 50:0a:09:83:80:91:96:6e   read_data 0 node_uuid 129e1f94-5bab-11e5-9e99-07c86cc5b5aa  bad_eof 0   ctio_nohandle 0 portcfg_toplogy_change 0    avg_other_latency 0 instance_name port.0f   port_wwpn 50:0a:09:83:80:91:96:6e   ctio_noispexch 0    portcfg_flogi_rjt 0 dropped_atio 0  portlogout_abts_timeout 0   portcfg_flogi_timeout 0 recverr_framelen 0  login_affecting_prlo 0  total_logins 0  login_affecting_prli 0  portcfg_flogi_acc 0 frame_length_error 0


def inventory_netapp_api_fcp(parsed):
    for key, values in parsed.items():
        settings = {}
        if values["state"] not in ["online"]:
            continue

        if "speed" in values:
            settings["inv_speed"] = values["speed"]
        settings["inv_state"] = values["state"]
        yield key, settings


# interfaces : {
#    total_ops: 0,
#    read_ops: 0,               # rate/number
#    write_ops: 0               # rate/number
#    read_bytes: 0,              # rate/bytes
#    write_bytes: 0              # rate/bytes
#    data_link_rate: 0          # bytes
#    avg_latency: 0,        # ms
#    avg_read_latency: 0,   # ms
#    avg_write_latency: 0,  # ms
#    discarded_frames: 0,       # rate/number
#    receive_error: 0,          # rate/number
#    state: "up"                # state
#    address: "50:0a:09:81:80:71:13:8f" # address
# }


def check_netapp_api_fcp(item, params, parsed):
    fcp_if = parsed.get(item)
    if not fcp_if:
        return

    yield from _io_bytes_results(item, params, fcp_if)
    yield from _speed_result(params, fcp_if)

    # this may be in the details *or* summary:
    state_str = fcp_if["state"]
    yield _notice_only_fy(0 if state_str == "online" else 2, f"State: {state_str}", [])

    # the rest will be in the details.
    yield from _io_ops_results(item, params, fcp_if)
    yield from _latency_results(item, params, fcp_if)

    # Address - details always.
    if "address" in fcp_if:
        yield _notice_only_fy(0, "Address %s" % fcp_if["address"], [])


# in netapp_ontap_fcp.py this function is ready for migration
def _speed_result(params, fcp_if):
    speed = fcp_if.get("speed")
    speed_str = None if speed is None else render.nicspeed(float(speed) / 8.0)
    expected_speed = params.get("speed", params.get("inv_speed"))
    expected_speed_str = (
        None if expected_speed is None else render.nicspeed(float(expected_speed) / 8.0)
    )

    if speed is None:
        if expected_speed is not None:
            yield 1, f"Speed: unknown (expected: {expected_speed_str})"
        return

    if expected_speed is None or speed == expected_speed:
        yield 0, f"Speed: {speed_str}"
        return

    yield 2, f"Speed: {speed_str} (expected: {expected_speed_str})"


# in netapp_ontap_fcp.py this function is ready for migration
def _io_bytes_results(item, params, fcp_if):
    bw_levels = bandwidth_levels(
        params=params,
        speed_in=fcp_if.get("speed"),
        speed_out=None,
        speed_total=None,
        unit=BandwidthUnit.BYTE,
    )

    value_store = get_value_store()
    now = fcp_if["now"]
    for what, levels, descr in [
        ("read_bytes", bw_levels.input, "Read"),
        ("write_bytes", bw_levels.output, "Write"),
    ]:
        value = get_rate(value_store, f"{item}.{what}", now, fcp_if.get(what), raise_overflow=True)
        if value is None:  # cannot happen. left in until migration, to illustrate intention.
            continue

        yield check_levels(
            value,
            what,
            (
                levels.config
                if isinstance(
                    levels,
                    PredictiveLevels,
                )
                else (
                    levels.upper
                    or (
                        None,
                        None,
                    )
                )
                + (
                    levels.lower
                    or (
                        None,
                        None,
                    )
                )
            ),
            human_readable_func=render.iobandwidth,
            infoname=descr,
        )


# in netapp_ontap_fcp.py this function is ready for migration
def _io_ops_results(item, params, fcp_if):
    now = fcp_if["now"]
    value_store = get_value_store()
    for what, descr in [
        ("read_ops", "Read OPS"),
        ("write_ops", "Write OPS"),
    ]:
        value = get_rate(value_store, f"{item}.{what}", now, fcp_if.get(what), raise_overflow=True)
        if value is None:  # cannot happen. left in until migration, to illustrate intention.
            continue

        yield _notice_only_fy(
            *check_levels(
                value,
                what,
                None,
                human_readable_func=int,
                infoname=descr,
            )
        )


# in netapp_ontap_fcp.py this function is ready for migration
def _latency_results(item, params, fcp_if):
    total_ops = fcp_if["total_ops"]
    value_store = get_value_store()
    for what, text in [
        ("avg_latency", "Latency"),
        ("avg_read_latency", "Read Latency"),
        ("avg_write_latency", "Write Latency"),
    ]:
        try:
            # According to NetApp's "Performance Management Design Guide",
            # the latency is a function of `total_ops`.
            value = get_rate(
                value_store, f"{item}.{what}", total_ops, fcp_if.get(what), raise_overflow=True
            )
        except IgnoreResultsError:
            continue

        yield _notice_only_fy(
            *check_levels(
                value,
                "%s_latency" % what,
                params.get(what),
                unit="ms",
                infoname=text,
            )
        )


def _notice_only_fy(state, text, metrics):
    """mimic behaviour of notice_only kwarg of new check_levels to the extend possible"""
    newline = "" if state else "\n"
    return state, f"{newline}{text}", metrics


def parse_netapp_api_fcp(string_table):
    now = time.time()
    parsed = netapp_api_parse_lines(string_table, custom_keys=["node_name", "instance_name"])
    fcp_interfaces = {}
    for key, values in parsed.items():
        fcp_data = {
            "state": values.get("state"),
            "address": values.get("port_wwpn"),
            "now": now,
            "total_ops": get_and_try_cast_to_int("total_ops", values, 0),
        }
        speed = get_and_try_cast_to_int("data-link-rate", values, 0) * 1000**3
        if speed:
            fcp_data["speed"] = speed

        for what in ["read_ops", "write_ops", "read_data", "write_data"]:
            if what in values:
                fcp_data[what.replace("data", "bytes")] = get_and_try_cast_to_int(what, values)

        for what in ["avg_latency", "avg_read_latency", "avg_write_latency"]:
            if what in values:
                fcp_data[what] = get_and_try_cast_to_int(what, values) / 1000.0
        fcp_interfaces[key] = fcp_data

    return fcp_interfaces


check_info["netapp_api_fcp"] = LegacyCheckDefinition(
    parse_function=parse_netapp_api_fcp,
    service_name="Interface FCP %s",
    discovery_function=inventory_netapp_api_fcp,
    check_function=check_netapp_api_fcp,
    check_ruleset_name="fcp",
    check_default_parameters={},
)
