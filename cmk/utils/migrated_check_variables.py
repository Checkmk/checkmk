#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
When migrating a check plugin to the new check API the corresponding check context
and check variables potentially needed to resolve the parameters saved in the autochecks
file will not be present any more. You can add those variables here, in oder to be able
to resolve the variables in saved autochecks.

This will also have the effect, that variables defined in a *.mk file in etc/check_mk/conf.d
will be considered.

For example: When migrating the check plugin `icom_repeater` we must add the following line
to this module, in order to be able to read and parse the autochecks discovered pre checkmk
1.7:

icom_ps_volt_default_levels = (13.5, 13.2, 14.1, 14.4)

"""

# chrony:
ntp_default_levels = (10, 200.0, 500.0)  # stratum, ms sys_time_offset_offset

# hr_mem (amongst others)
memused_default_levels = (150.0, 200.0)

# netscaler_vserver
netscaler_vserver_states = {
    "0": (1, "unknown"),
    "1": (2, "down"),
    "2": (1, "unknown"),
    "3": (1, "busy"),
    "4": (1, "out of service"),
    "5": (1, "transition to out of service"),
    "7": (0, "up"),
}
netscaler_vserver_types = {
    "0": "http",
    "1": "ftp",
    "2": "tcp",
    "3": "udp",
    "4": "ssl bridge",
    "5": "monitor",
    "6": "monitor udp",
    "7": "nntp",
    "8": "http server",
    "9": "http client",
    "10": "rpc server",
    "11": "rpc client",
    "12": "nat",
    "13": "any",
    "14": "ssl",
    "15": "dns",
    "16": "adns",
    "17": "snmp",
    "18": "ha",
    "19": "monitor ping",
    "20": "sslOther tcp",
    "21": "aaa",
    "23": "secure monitor",
    "24": "ssl vpn udp",
    "25": "rip",
    "26": "dns client",
    "27": "rpc server",
    "28": "rpc client",
    "62": "service unknown",
    "69": "tftp",
}
netscaler_vserver_entitytypes = {
    "0": "unknown",
    "1": "loadbalancing",
    "2": "loadbalancing group",
    "3": "ssl vpn",
    "4": "content switching",
    "5": "cache redirection",
}

# ps
ps_default_levels = {"levels": (1, 1, 99999, 99999)}
