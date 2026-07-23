#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.ccc import tty
from cmk.ccc.site import SiteId
from cmk.gui.config import load_config
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.post_rename_site.internal import (
    Name,
    RenameAction,
    SortIndex,
    Title,
)
from cmk.utils.log import console


def warn_about_renamed_remote_site(
    old_site_id: SiteId, new_site_id: SiteId, logger: Logger
) -> None:
    """Warn user about central site that needs to be updated manually

    Detect whether or not this is a remote site and issue a warning to let the user known"""
    if not is_distributed_setup_remote_site(load_config().sites):
        return

    logger.info("")
    console.warning(
        tty.format_warning(
            "You renamed a distributed remote site.\n\nTo make your distributed "
            'setup work again, you will have to update the "Distributed Monitoring" '
            "configuration in your central site.\n"
        )
    )


rename_action_warn_remote_site = RenameAction(
    name=Name("warn_remote_site"),
    title=Title("Warn about renamed remote site"),
    sort_index=SortIndex(950),
    run=warn_about_renamed_remote_site,
)
