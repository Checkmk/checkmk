#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'esx_vsphere_sensors'

info = [['Dummy sensor', '', '', '', '', '', 'green', 'all is good', 'the sun is shining']]

discovery = {'': [(None, [])]}

checks = {
    '': [(None, {}, [(0, ('All sensors are in normal state\n'
                          'Sensors operating normal are:\n'
                          'Dummy sensor: all is good (the sun is shining)'), [])])]
}
