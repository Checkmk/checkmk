#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# output from the nutanix prism plugin is well-formed tsv
# (tab-separated-values) with a header row
def parse_prism(info):
    result = []
    header = info[0]
    for row in info[1:]:
        result.append(dict(zip(header, row)))
    return result
