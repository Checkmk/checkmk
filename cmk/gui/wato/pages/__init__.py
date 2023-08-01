#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageRegistry
from cmk.gui.wato.mode import ModeRegistry

from . import (
    activate_changes,
    automation,
    backup,
    diagnostics,
    fetch_agent_output,
    folders,
    host_diagnose,
    services,
    sites,
    user_profile,
)


def register(page_registry: PageRegistry, mode_registry: ModeRegistry) -> None:
    diagnostics.register(page_registry, mode_registry)
    user_profile.mega_menu.register(page_registry)
    user_profile.two_factor.register(page_registry)
    user_profile.two_factor.register(page_registry)
    user_profile.edit_profile.register(page_registry)
    user_profile.change_password.register(page_registry)
    user_profile.async_replication.register(page_registry)
    user_profile.replicate.register(page_registry)
    services.register(page_registry, mode_registry)
    host_diagnose.register(page_registry, mode_registry)
    activate_changes.register(page_registry, mode_registry)
    backup.register(page_registry, mode_registry)
    folders.register(page_registry, mode_registry)
    automation.register(page_registry)
    sites.register(page_registry, mode_registry)
    fetch_agent_output.register(page_registry)
