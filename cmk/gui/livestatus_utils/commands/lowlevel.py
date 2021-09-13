#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any, List, Optional

# TODO: typing of connection when livestatus.py is on pypi
from livestatus import SiteId

from cmk.utils.site import omd_site

from cmk.gui.livestatus_utils.commands.type_defs import LivestatusCommand


def send_command(
    connection,
    command: LivestatusCommand,
    params: List[Any],
    site_id: Optional[SiteId] = None,
):
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

    Examples:

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> with simple_expect(
        ...         "COMMAND [...] ADD_HOST_COMMENT", match_type="ellipsis") as live:
        ...      send_command(live, "ADD_HOST_COMMENT", [])

        >>> with simple_expect(
        ...          "COMMAND [...] ADD_HOST_COMMENT;1;2;3", match_type="ellipsis") as live:
        ...      send_command(live, "ADD_HOST_COMMENT", [1, 2, 3])

        >>> with simple_expect(
        ...         "COMMAND [...] ADD_HOST_COMMENT;1;2;3", match_type="ellipsis") as live:
        ...      send_command(live, "ADD_HOST_COMMENT", [object()])
        Traceback (most recent call last):
        ...
        ValueError: Unknown type of parameter 0: <class 'object'>

    """
    current_time = int(time.time())
    cmd: str = command
    for pos, param in enumerate(params):
        if not isinstance(param, (int, str)):
            raise ValueError(f"Unknown type of parameter {pos}: {type(param)}")
        cmd += f";{param}"

    if not site_id:
        site_id = omd_site()
    connection.command(f"[{current_time}] {cmd}", sitename=site_id)
