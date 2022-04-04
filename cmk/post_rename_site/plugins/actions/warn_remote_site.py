#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import SiteId

from cmk.utils.i18n import _
from cmk.utils.log.console import warning

from cmk.gui.site_config import is_wato_slave_site

from cmk.post_rename_site.main import logger
from cmk.post_rename_site.registry import rename_action_registry, RenameAction


def warn_about_renamed_remote_site(old_site_id: SiteId, new_site_id: SiteId) -> None:
    """Warn user about central site that needs to be updated manually

    Detect whether or not this is a remote site and issue a warning to let the user known"""
    if not is_wato_slave_site():
        return

    logger.info("")
    warning(
        "You renamed a distributed remote site.\n\nTo make your distributed "
        'setup work again, you will have to update the "Distributed Monitoring" '
        "configuration in your central site.\n"
    )


rename_action_registry.register(
    RenameAction(
        name="warn_remote_site",
        title=_("Warn about renamed remote site"),
        sort_index=950,
        handler=warn_about_renamed_remote_site,
    )
)
