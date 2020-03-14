#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Scan Function for DOCSIS Devices who supports the general information
def docsis_scan_function(oid):
    return oid(".1.3.6.1.2.1.1.2.0") in [
        ".1.3.6.1.4.1.4115.820.1.0.0.0.0.0",  # ARRIS Touchstone WideBand Cable Modem
        ".1.3.6.1.4.1.4115.900.2.0.0.0.0.0",  # ARRIS Touchstone Cable Modem HW REV:2
        ".1.3.6.1.4.1.9.1.827",  # Cisco CMTS UBR 7200
        ".1.3.6.1.4.1.4998.2.1",  # ARRIS CMTS C4
        ".1.3.6.1.4.1.20858.2.600",  # CASA C100G
    ]


# Scan Function for cable modems with DOCSIS MIB
# docsIfCmStatusTable     1.3.6.1.2.1.10.127.1.2.2
def docsis_scan_function_cable_modem(oid):
    return oid(".1.3.6.1.2.1.1.2.0") in [
        ".1.3.6.1.4.1.4115.820.1.0.0.0.0.0",  # ARRIS Touchstone WideBand Cable Modem
        ".1.3.6.1.4.1.4115.900.2.0.0.0.0.0",  # ARRIS Touchstone Cable Modem HW REV:2
    ]
