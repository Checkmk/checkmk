#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..agent_based_api.v1 import (
    all_of,
    any_of,
    exists,
    startswith,
)

DETECT = any_of(
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11096.6"),
    # e.g. HM800 report "linux" as type. Check the vendor tree too
    all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        exists(".1.3.6.1.4.1.11096.6.1.*"),
    ))
