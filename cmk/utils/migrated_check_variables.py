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
