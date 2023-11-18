#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import all_of, exists, not_exists, startswith

DETECT_AKCP_EXP = all_of(
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3854.1"), exists(".1.3.6.1.4.1.3854.2.*")
)

DETEC_AKCP_SP2PLUS = all_of(
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3854"),
    exists(".1.3.6.1.4.1.3854.3.*"),
    not_exists(".1.3.6.1.4.1.3854.2.*"),
)
