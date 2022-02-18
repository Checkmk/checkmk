#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains helpers to set comments for host and service.
"""
import datetime as dt

from cmk.gui.globals import user as _user
from cmk.gui.livestatus_utils.commands.lowlevel import send_command
from cmk.gui.livestatus_utils.commands.utils import to_timestamp


def force_schedule_host_check(connection, host_name: str, check_time: dt.datetime):
    """Schedule a forced active check of a particular host

    Args:
        connection:
            A livestatus connection object

        host_name:
            The name of the host where the forced check should be performed on

        check_time:
            The time at which this forced check should be performed

    Examples:
        >>> import pytz
        >>> _check_time = dt.datetime(1970, 1, 1, tzinfo=pytz.timezone("UTC"))

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.config import load_config
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.utils.logged_in import SuperUserContext

        >>> cmd = "COMMAND [...] SCHEDULE_FORCED_HOST_CHECK;example.com;0"
        >>> expect = simple_expect(cmd, match_type="ellipsis")
        >>> with expect as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     force_schedule_host_check(live, 'example.com', _check_time)

    """
    _user.need_permission("action.reschedule")

    return send_command(
        connection, "SCHEDULE_FORCED_HOST_CHECK", [host_name, to_timestamp(check_time)]
    )


def force_schedule_service_check(
    connection, host_name: str, service_description: str, check_time: dt.datetime
):
    """Schedule a forced active check of a particular service

    Args:
        connection:
            A livestatus connection object

        host_name:
            The name of the host where the service is

        service_description:
            The service description for which the forced check should be performed on

        check_time:
            The time at which this forced check should be performed

    Examples:
        >>> import pytz
        >>> _check_time = dt.datetime(1970, 1, 1, tzinfo=pytz.timezone("UTC"))

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.config import load_config
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.utils.logged_in import SuperUserContext

        >>> cmd = "COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;example.com;CPU Load;0"
        >>> expect = simple_expect(cmd, match_type="ellipsis")
        >>> with expect as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     force_schedule_service_check(live,'example.com', 'CPU Load', _check_time)
    """
    _user.need_permission("action.reschedule")

    return send_command(
        connection,
        "SCHEDULE_FORCED_SVC_CHECK",
        [host_name, service_description, to_timestamp(check_time)],
    )
