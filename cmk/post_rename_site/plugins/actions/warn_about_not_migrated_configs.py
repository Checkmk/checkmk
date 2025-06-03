#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.ccc import tty
from cmk.ccc.i18n import _
from cmk.ccc.site import SiteId

from cmk.utils.log import console

from cmk.post_rename_site.registry import rename_action_registry, RenameAction


def warn_about_configs_to_review(old_site_id: SiteId, new_site_id: SiteId, logger: Logger) -> None:
    logger.info("")
    console.warning(
        tty.format_warning(
            "Some configs may need to be reviewed\n\n"
            "Parts of the site configuration cannot be migrated automatically. The following\n"
            "parts of the configuration may have to be reviewed and adjusted manually:\n\n"
            "- Custom bookmarks (in users bookmark lists)\n"
            "- Hard coded site filters in custom dashboards, views, reports\n"
            "- Path in rrdcached journal files\n"
            "- NagVis maps or custom NagVis backend settings\n"
            '- Notification rule "site" conditions\n'
            '- Event Console rule "site" conditions\n'
            '- "site" field in "Agent updater (Linux, Windows, Solaris)" rules (CEE/CME only)\n'
            '- Alert handler rule "site" conditions (CEE/CME only)\n'
        )
    )


rename_action_registry.register(
    RenameAction(
        name="warn_about_configs_to_review",
        title=_("Warn about configurations to review"),
        sort_index=960,
        handler=warn_about_configs_to_review,
    )
)
