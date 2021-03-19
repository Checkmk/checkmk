#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any, List

from cmk.gui import config
from cmk.gui.plugins.openapi.livestatus_helpers.commands.type_defs import LivestatusCommand

# TODO: typing of connection when livestatus.py is on pypi


def send_command(
    connection,
    command: LivestatusCommand,
    params: List[Any],
):
    """Send a command to livestatus.

    Args:
        connection:
            A livestatus connection object.

        command:
            The livestatus external command to be sent. For reference on these commands have a look
            at this page: https://checkmk.com/cms_livestatus_references.html

        params:
            A list of anything.

    Examples:

        >>> from cmk.gui.plugins.openapi.livestatus_helpers.testing import simple_expect
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
    connection.command(f"[{current_time}] {cmd}", sitename=config.omd_site())
