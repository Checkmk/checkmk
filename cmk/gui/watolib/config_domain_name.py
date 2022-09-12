#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum


class ConfigDomainName(enum.Enum):
    APACHE = "apache"
    CA_CERTIFICATE = "ca-certificates"
    CORE = "check_mk"
    DCD = "dcd"
    DISKSPACE = "diskspace"
    EVENT_CONSOLE = "ec"
    GUI = "multisite"
    LIVEPROXY = "liveproxyd"
    MK_NOTIFYD = "mknotifyd"
    OMD = "omd"
    RRD_CACHED = "rrdcached"
