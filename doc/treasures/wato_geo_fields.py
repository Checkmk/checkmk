#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# place this file to ~/local/share/check_mk/web/plugins/wato to get two new fields in the wato host properties.
# this fields can be used to add Latiude and Longitude information. Useful for the Nagvis Geomap

declare_host_attribute(
    NagiosTextAttribute(
        "lat",
        "_LAT",
        "Latitude",
        "Latitude",
    ),
    show_in_table=False,
    show_in_folder=False,
)

declare_host_attribute(
    NagiosTextAttribute(
        "long",
        "_LONG",
        "Longitude",
        "Longitude",
    ),
    show_in_table=False,
    show_in_folder=False,
)
