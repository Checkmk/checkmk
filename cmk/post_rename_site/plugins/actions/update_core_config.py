#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess

from livestatus import SiteId

from cmk.utils.i18n import _

from cmk.post_rename_site.registry import rename_action_registry, RenameAction


def update_core_config(old_site_id: SiteId, new_site_id: SiteId) -> None:
    """After all the changes to the configuration finally trigger a core config update"""
    subprocess.check_call(["cmk", "-U"])


rename_action_registry.register(
    RenameAction(
        name="update_core_config",
        title=_("Update core config"),
        sort_index=900,
        handler=update_core_config,
    )
)
