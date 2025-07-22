#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import matches, startswith

DETECT_6100 = matches(".1.3.6.1.2.1.1.1.0", "Aruba.+6100.*")
DETECT_2930M = matches(".1.3.6.1.2.1.1.1.0", "Aruba.+2930M.*")
DETECT_WLC = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14823.1.1")
