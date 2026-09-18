#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.ccc.hostaddress import HostName


# Gets replaced by the actual implementation in commercial editions
def try_bake_agents_for_hosts(hosts: Sequence[HostName], *, debug: bool) -> None:
    pass


# Gets replaced by the actual implementation in commercial editions
def try_bake_agents_on_activation(*, call_site: str, use_git: bool, debug: bool) -> None:
    """Bake all hosts' agents as a side effect of activating a configuration change

    In contrast to `try_bake_agents_for_hosts` this runs synchronously: the caller is a
    background job that must not report success before the agents are up to date.
    """
