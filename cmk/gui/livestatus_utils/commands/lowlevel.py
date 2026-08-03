#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from typing import Any

from cmk.ccc.site import omd_site, SiteId
from cmk.gui.livestatus_utils.commands.type_defs import LivestatusCommand
from cmk.livestatus_client import MultiSiteConnection


def send_command(
    connection: MultiSiteConnection,
    command: LivestatusCommand,
    params: list[Any],
    site_id: SiteId | None = None,
) -> None:
    """Send a command to livestatus.

    Args:
        connection:
            A livestatus connection object.

        command:
            The livestatus external command to be sent. For reference on these commands have a look
            at this page: https://docs.checkmk.com/master/en/livestatus_references.html

        params:
            A list of anything.

        site_id:
            The site name

    """
    current_time = int(time.time())
    cmd: str = command
    for pos, param in enumerate(params):
        if not isinstance(param, int | str):
            raise ValueError(f"Unknown type of parameter {pos}: {type(param)}")
        cmd += f";{param}"

    if not site_id:
        site_id = omd_site()
    connection.command(f"[{current_time}] {cmd}", sitename=site_id)
