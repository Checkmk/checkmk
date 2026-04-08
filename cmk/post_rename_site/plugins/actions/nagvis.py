#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from logging import Logger
from pathlib import Path

from cmk.ccc import store
from cmk.ccc.site import SiteId
from cmk.post_rename_site.internal import (
    Name,
    RenameAction,
    SortIndex,
    Title,
)
from cmk.utils import paths


def update_nagvis_maps(
    old_site_id: SiteId,
    new_site_id: SiteId,
    logger: Logger,
    omd_root: Path = paths.omd_root,
) -> None:
    """Update backend references in NagVis map config files

    NagVis map files can contain objects with a backend attribute referencing the site ID,
    e.g. ``backend=old_site_id``. These need to be updated to the new site ID.
    """
    maps_dir = omd_root / "etc/nagvis/maps"
    if not maps_dir.is_dir():
        return

    # NagVis backend IDs created by Checkmk are unquoted (e.g. ``backend=mysite``).
    # The pattern deliberately only matches exact unquoted values so that lines with
    # inline comments or a quoted value are left untouched.
    pattern = re.compile(
        r"^(\s*backend\s*=\s*)" + re.escape(str(old_site_id)) + r"(\s*)$",
        re.MULTILINE,
    )

    for map_file in maps_dir.glob("*.cfg"):
        try:
            content = map_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning("NagVis map %s: skipping, file is not valid UTF-8", map_file.name)
            continue
        new_content, count = pattern.subn(
            lambda m: m.group(1) + str(new_site_id) + m.group(2), content
        )
        if count:
            logger.debug("NagVis map %s: Updated %d backend reference(s)", map_file.name, count)
            store.save_text_to_file(map_file, new_content)


rename_action_nagvis_maps = RenameAction(
    name=Name("nagvis_maps"),
    title=Title("NagVis maps"),
    sort_index=SortIndex(20),
    run=update_nagvis_maps,
)
