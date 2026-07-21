#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.post_rename_site.internal import (
    Name,
    RenameAction,
    SortIndex,
    Title,
)
from cmk.ruleset_matcher.labels import BuiltinLabelsKey, update_builtin_host_labels


def update_builtin_host_labels_site(
    old_site_id: SiteId, new_site_id: SiteId, logger: Logger
) -> None:
    """Refresh the ``cmk/site`` builtin host label to the new site id"""
    logger.debug(
        "Updating cmk/site builtin host label to %(new_site_id)r", {"new_site_id": new_site_id}
    )
    update_builtin_host_labels(
        cmk.utils.paths.builtin_host_labels_file, {BuiltinLabelsKey.SITE: str(new_site_id)}
    )


rename_action_builtin_host_labels = RenameAction(
    name=Name("builtin_host_labels"),
    title=Title("Update builtin host labels"),
    sort_index=SortIndex(100),  # before update_core_config (900)
    run=update_builtin_host_labels_site,
)
