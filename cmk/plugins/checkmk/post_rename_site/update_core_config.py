#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from logging import Logger

from cmk.ccc.site import SiteId
from cmk.post_rename_site.internal import (
    Name,
    RenameAction,
    SortIndex,
    Title,
)


def update_core_config(old_site_id: SiteId, new_site_id: SiteId, logger: Logger) -> None:
    """After all the changes to the configuration finally trigger a core config update"""
    subprocess.check_call(["cmk", "-U"])


rename_action_update_core_config = RenameAction(
    name=Name("update_core_config"),
    title=Title("Update core config"),
    sort_index=SortIndex(900),
    run=update_core_config,
)
