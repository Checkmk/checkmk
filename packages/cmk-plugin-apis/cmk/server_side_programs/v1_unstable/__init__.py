#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
WARNING
-------

**This version of the API is work in progress and not yet stable.
It is not recommended to use this version in production systems.**

**However: we do intend to stabilize this API version in the future and release it,
so you are encouraged to experiment and give us feedback.**


Scope
-----

This API provides functionality to be used by server-side programs
running on the Checkmk server.
It is written with special agents and active checks in mind -- we do
not guarantee they work in other circumstances.

This is the first version of the server-side programs API.

"""

from ._crash_reporting import report_agent_crashes as report_agent_crashes
from ._crash_reporting import report_check_crashes as report_check_crashes
from ._host_name_validation import (
    HostnameValidationAdapter as HostnameValidationAdapter,
)
from ._storage import Storage as Storage
from ._vcrtrace import vcrtrace as vcrtrace

__all__ = [
    "HostnameValidationAdapter",
    "Storage",
    "vcrtrace",
    "report_agent_crashes",
]
