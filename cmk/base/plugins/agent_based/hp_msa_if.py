#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register, type_defs
from .utils import hp_msa, interfaces

# <<<hp_msa_if>>>
# port 3 durable-id hostport_A1
# port 3 controller A
# port 3 controller-numeric 1
# port 3 port A1
# port 3 port-type FC
# port 3 port-type-numeric 6
# port 3 media FC(P)
# port 3 target-id 207000c0ff1e82bb
# port 3 status Up
# port 3 status-numeric 0
# port 3 actual-speed 8Gb
# port 3 actual-speed-numeric 7
# port 3 configured-speed Auto
# port 3 configured-speed-numeric 3
# port 3 health OK
# port 3 health-numeric 0
# port 3 health-reason
# port 3 health-recommendation
# fc-port 4 configured-topology PTP
# fc-port 4 primary-loop-id N/A
# fc-port 4 sfp-status OK
# fc-port 4 sfp-present Present
# fc-port 4 sfp-present-numeric 1
# fc-port 4 sfp-vendor DHS
# fc-port 4 sfp-part-number FTLF8529P3BCV-1H
# fc-port 4 sfp-revision A
# fc-port 4 sfp-supported-speeds 4G,8G,16G
# port 5 durable-id hostport_A2
# port 5 controller A
# port 5 controller-numeric 1
# port 5 port A2
# port 5 port-type FC
# port 5 port-type-numeric 6
# port 5 media FC(P)
# port 5 target-id 217000c0ff1e82bb
# port 5 status Up
# port 5 status-numeric 0
# port 5 actual-speed 8Gb
# port 5 actual-speed-numeric 7
# port 5 configured-speed Auto
# port 5 configured-speed-numeric 3
# port 5 health OK
# port 5 health-numeric 0
# port 5 health-reason
# port 5 health-recommendation
# fc-port 6 configured-topology PTP
# fc-port 6 primary-loop-id N/A
# fc-port 6 sfp-status OK
# fc-port 6 sfp-present Present
# fc-port 6 sfp-present-numeric 1
# fc-port 6 sfp-vendor DHS
# fc-port 6 sfp-part-number FTLF8529P3BCV-1H
# fc-port 6 sfp-revision A
# fc-port 6 sfp-supported-speeds 4G,8G,16G
# host-port-statistics 1 durable-id hostport_A1
# host-port-statistics 1 bytes-per-second 8881.6KB
# host-port-statistics 1 bytes-per-second-numeric 8881664
# host-port-statistics 1 iops 106
# host-port-statistics 1 number-of-reads 23978726
# host-port-statistics 1 number-of-writes 157185192
# host-port-statistics 1 data-read 2583.7GB
# host-port-statistics 1 data-read-numeric 2583779790336
# host-port-statistics 1 data-written 12.7TB
# host-port-statistics 1 data-written-numeric 12760541957120
# host-port-statistics 1 queue-depth 0
# host-port-statistics 1 avg-rsp-time 1355
# host-port-statistics 1 avg-read-rsp-time 7872
# host-port-statistics 1 avg-write-rsp-time 497
# host-port-statistics 1 reset-time 2015-05-22 13:54:37
# host-port-statistics 1 reset-time-numeric 1432302877
# host-port-statistics 1 start-sample-time 2015-08-21 11:51:43
# host-port-statistics 1 start-sample-time-numeric 1440157903
# host-port-statistics 1 stop-sample-time 2015-08-21 11:52:00
# host-port-statistics 1 stop-sample-time-numeric 1440157920
# host-port-statistics 2 durable-id hostport_A2
# host-port-statistics 2 bytes-per-second 5161.9KB
# host-port-statistics 2 bytes-per-second-numeric 5161984
# host-port-statistics 2 iops 220
# host-port-statistics 2 number-of-reads 43445061
# host-port-statistics 2 number-of-writes 343467343
# host-port-statistics 2 data-read 5127.7GB
# host-port-statistics 2 data-read-numeric 5127720481792
# host-port-statistics 2 data-written 28.0TB
# host-port-statistics 2 data-written-numeric 28069848090624
# host-port-statistics 2 queue-depth 0
# host-port-statistics 2 avg-rsp-time 1492
# host-port-statistics 2 avg-read-rsp-time 5309
# host-port-statistics 2 avg-write-rsp-time 1129
# host-port-statistics 2 reset-time 2015-05-22 13:54:37
# host-port-statistics 2 reset-time-numeric 1432302877
# host-port-statistics 2 start-sample-time 2015-08-21 11:51:43
# host-port-statistics 2 start-sample-time-numeric 1440157903
# host-port-statistics 2 stop-sample-time 2015-08-21 11:52:00
# host-port-statistics 2 stop-sample-time-numeric 1440157920


def parse_hp_msa_if(string_table: type_defs.StringTable) -> interfaces.Section:
    parsed = []
    for idx, (_key, values) in enumerate(sorted(hp_msa.parse_hp_msa(string_table).items())):
        try:
            speed = int(values["actual-speed"].replace("Gb", "")) * 10**9
        except ValueError:
            speed = 0

        if values["status"] == "Up":
            status = "1"
        else:
            status = "2"

        parsed.append(
            interfaces.Interface(
                index=str(idx + 1),
                descr=values["port"],
                alias="",
                type="6",
                speed=speed,
                oper_status=status,
                in_octets=int(values["data-read-numeric"]),
                out_octets=int(values["data-written-numeric"]),
                out_qlen=int(values["queue-depth"]),
            )
        )

    return parsed


register.agent_section(
    name="hp_msa_if",
    parse_function=parse_hp_msa_if,
    parsed_section_name="interfaces",
)
