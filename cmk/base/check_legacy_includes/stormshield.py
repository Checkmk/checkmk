#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def stormshield_scan_function(oid):
    return (
        oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.8072")
        or oid(".1.3.6.1.2.1.1.2.0") == ".1.3.6.1.4.1.11256.2.0"  # version >= 3.7.18
    ) and oid(".1.3.6.1.4.1.11256.1.0.1.0")


def stormshield_cluster_scan_function(oid):
    # We have to use a different scan function here, so we only try getting
    # our snmp_info if information about the cluster exists
    return (
        oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.8072.3.2.8")
        or oid(".1.3.6.1.2.1.1.2.0") == ".1.3.6.1.4.1.11256.2.0"  # version >= 3.7.18
    ) and oid(".1.3.6.1.4.1.11256.1.11.*")
