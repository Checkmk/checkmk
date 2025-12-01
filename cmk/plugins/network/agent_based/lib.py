#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import startswith

DETECT_CISCO = startswith(".1.3.6.1.2.1.1.2.0", "1.3.6.1.4.1.9")
DETECT_FORTINET = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356")
DETECT_MERAKI = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.29671")
