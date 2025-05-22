#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.ccc.hostaddress import HostName


# Get's replaced by the actual implementation in non CRE editions
def try_bake_agents_for_hosts(hosts: Sequence[HostName], *, debug: bool) -> None:
    pass
