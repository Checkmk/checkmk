#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import cmk.utils.version as cmk_version
from cmk.utils.type_defs import HostName

from cmk.gui.background_job import BackgroundJobAlreadyRunning


def has_agent_bakery() -> bool:
    return not cmk_version.is_raw_edition()


def try_bake_agents_for_hosts(hosts: Sequence[HostName]) -> None:
    if has_agent_bakery():
        import cmk.gui.cee.plugins.wato.agent_bakery.misc as agent_bakery  # pylint: disable=import-error,no-name-in-module

        try:
            agent_bakery.start_bake_agents(host_names=hosts, signing_credentials=None)
        except BackgroundJobAlreadyRunning:
            pass
