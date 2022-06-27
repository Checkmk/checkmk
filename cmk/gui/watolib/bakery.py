#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List

import cmk.utils.version as cmk_version
from cmk.utils.type_defs import HostName

from cmk.gui.background_job import BackgroundJobAlreadyRunning


def has_agent_bakery() -> bool:
    return not cmk_version.is_raw_edition()


def try_bake_agents_for_hosts(hosts: List[HostName]) -> None:
    if has_agent_bakery():
        import cmk.gui.cee.plugins.wato.agent_bakery.misc as agent_bakery  # pylint: disable=import-error,no-name-in-module

        try:
            agent_bakery.start_bake_agents(host_names=hosts, signing_credentials=None)
        except BackgroundJobAlreadyRunning:
            pass


def ruleset_changed(name: str) -> None:
    if has_agent_bakery():
        import cmk.gui.cee.agent_bakery as agent_bakery  # pylint: disable=no-name-in-module

        agent_bakery.ruleset_changed(name)
