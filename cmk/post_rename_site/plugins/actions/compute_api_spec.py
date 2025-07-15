#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from logging import Logger

from cmk.ccc.i18n import _
from cmk.ccc.site import SiteId

from cmk.post_rename_site.registry import rename_action_registry, RenameAction


def compute_api_spec(old_site_id: SiteId, new_site_id: SiteId, logger: Logger) -> None:
    subprocess.check_call(["cmk-compute-api-spec"])


rename_action_registry.register(
    RenameAction(
        name="compute_api_spec",
        title=_("Compute REST API specification"),
        sort_index=950,
        handler=compute_api_spec,
    )
)
