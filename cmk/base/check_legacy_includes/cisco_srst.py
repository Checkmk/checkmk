#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.9.9.441.1.2.1.0 2 --> CISCO-SRST-MIB::csrstEnabled.0, 1:enabled, 2:disable

# .1.3.6.1.4.1.9.9.441.1.3.1.0 2 --> CISCO-SRST-MIB::csrstState.0, 1:active, 2:inactive
# .1.3.6.1.4.1.9.9.441.1.3.2.0 0 --> CISCO-SRST-MIB::csrstSipPhoneCurrentRegistered.0
# .1.3.6.1.4.1.9.9.441.1.3.3.0 0 --> CISCO-SRST-MIB::csrstSipCallLegs.0
# .1.3.6.1.4.1.9.9.441.1.3.4.0 0 --> CISCO-SRST-MIB::csrstTotalUpTime.0


def cisco_srst_scan_function(oid):
    return (
        "cisco" in oid(".1.3.6.1.2.1.1.1.0").lower() and oid(".1.3.6.1.4.1.9.9.441.1.2.1.0") == "1"
    )
