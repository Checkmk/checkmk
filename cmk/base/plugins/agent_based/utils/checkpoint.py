#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..agent_based_api.v1 import (
    all_of,
    any_of,
    startswith,
    matches,
)

DETECT = all_of(
    any_of(
        matches(".1.3.6.1.2.1.1.1.0", "[^ ]+ [^ ]+ [^ ]*cp( .*)?"),
        startswith(".1.3.6.1.2.1.1.1.0", "IPSO "),
        matches(".1.3.6.1.2.1.1.1.0", "Linux.*cpx.*"),
    ),
    startswith(".1.3.6.1.4.1.2620.1.1.21.0", 'firewall'),
)
