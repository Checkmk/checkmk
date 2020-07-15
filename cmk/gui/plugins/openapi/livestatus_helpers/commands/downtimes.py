#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict, Literal
import datetime as dt

from cmk.gui.plugins.openapi.livestatus_helpers.commands.lowlevel import send_command
from cmk.gui.plugins.openapi.livestatus_helpers.commands.type_defs import LivestatusCommand
from cmk.gui.plugins.openapi.livestatus_helpers.commands.utils import to_timestamp

RecurMode = Literal[
    "fixed",
    "hour",
    "day",
    "week",
    "second_week",
    "fourth_week",
    "weekday_start",
    "weekday_end",
    "day_of_month",
]  # yapf: disable


def del_host_downtime(connection, downtime_id: int):
    """Delete a host downtime.

    Args:
        connection:
            A livestatus connection object.

        downtime_id:
            The downtime-id.

    Examples:

        >>> from cmk.gui.plugins.openapi.livestatus_helpers.testing import simple_expect
        >>> with simple_expect("COMMAND [...] DEL_HOST_DOWNTIME;1") as live:
        ...     del_host_downtime(live, 1)

    """
    return send_command(connection, "DEL_HOST_DOWNTIME", [downtime_id])


def del_service_downtime(connection, downtime_id: int):
    """Delete a service downtime.

    Args:
        connection:
            A livestatus connection object.

        downtime_id:
            The downtime-id.

    Examples:

        >>> from cmk.gui.plugins.openapi.livestatus_helpers.testing import simple_expect
        >>> with simple_expect("COMMAND [...] DEL_SVC_DOWNTIME;1") as live:
        ...     del_service_downtime(live, 1)

    """
    return send_command(connection, "DEL_SVC_DOWNTIME", [downtime_id])


def schedule_service_downtime(
    connection,
    start_time: dt.datetime,
    end_time: dt.datetime,
    recur: RecurMode = 'fixed',
    trigger_id: int = 0,
    duration: int = 0,
    user_id: str = '',
    comment: str = '',
):
    """Schedule the downtime of a host.

    Args:
        connection:
            A livestatus connection object.

        start_time:
            When the downtime shall begin.

        end_time:
            When the downtime shall end.

        recur:
            The recurring mode of the new downtime. Available modes are:
                * fixed
                * hour
                * day
                * week
                * second_week
                * fourth_week
                * weekday_start
                * weekday_end
                * day_of_month

        trigger_id:
            The id of another downtime-entry. If given (other than 0) then this downtime will be
            triggered by the other downtime.

        duration:
            Duration in seconds. Gives the desired duration of the downtime. When set, the downtime
            begin somewhen between `start_time` and `end_time` and last for `duration` seconds.

        user_id:

        comment:
            A comment which will be added to the downtime.

    Examples:

        >>> import pytz
        >>> _start_time = dt.datetime(2020, 1, 1, tzinfo=pytz.timezone("UTC"))
        >>> _end_time = dt.datetime(2020, 1, 2, tzinfo=pytz.timezone("UTC"))

        >>> from cmk.gui.plugins.openapi.livestatus_helpers.testing import simple_expect
        >>> cmd = "COMMAND [...] SCHEDULE_SVC_DOWNTIME;1577836800;1577923200;17;0;120;;Boom"
        >>> with simple_expect(cmd) as live:
        ...     schedule_service_downtime(live,
        ...             _start_time,
        ...             _end_time,
        ...             recur="day_of_month",
        ...             duration=120,
        ...             comment="Boom")

    """
    return _schedule_downtime(
        connection,
        "SCHEDULE_SVC_DOWNTIME",
        start_time,
        end_time,
        recur,
        trigger_id,
        duration,
        user_id,
        comment,
    )


def schedule_host_downtime(
    connection,
    start_time: dt.datetime,
    end_time: dt.datetime,
    recur: RecurMode = 'fixed',
    trigger_id: int = 0,
    duration: int = 0,
    user_id: str = '',
    comment: str = '',
):
    """Schedule the downtime of a host.

    Args:
        connection:
            A livestatus connection object.

        start_time:
            When the downtime shall begin.

        end_time:
            When the downtime shall end.

        recur:
            The recurring mode of the new downtime. Available modes are:
                * fixed
                * hour
                * day
                * week
                * second_week
                * fourth_week
                * weekday_start
                * weekday_end
                * day_of_month

        trigger_id:
            The id of another downtime-entry. If given (other than 0) then this downtime will be
            triggered by the other downtime.

        duration:
            Duration in seconds. Gives the desired duration of the downtime. When set, the downtime
            begin somewhen between `start_time` and `end_time` and last for `duration` seconds.

        user_id:

        comment:
            A comment which will be added to the downtime.

    Examples:

        >>> import pytz
        >>> _start_time = dt.datetime(2020, 1, 1, tzinfo=pytz.timezone("UTC"))
        >>> _end_time = dt.datetime(2020, 1, 2, tzinfo=pytz.timezone("UTC"))

        >>> from cmk.gui.plugins.openapi.livestatus_helpers.testing import simple_expect
        >>> cmd = "COMMAND [...] SCHEDULE_HOST_DOWNTIME;1577836800;1577923200;17;0;120;;Boom"
        >>> with simple_expect(cmd) as live:
        ...     schedule_host_downtime(live,
        ...             _start_time,
        ...             _end_time,
        ...             recur="day_of_month",
        ...             duration=120,
        ...             comment="Boom")

    """
    return _schedule_downtime(
        connection,
        "SCHEDULE_HOST_DOWNTIME",
        start_time,
        end_time,
        recur,
        trigger_id,
        duration,
        user_id,
        comment,
    )


def _schedule_downtime(
    sites,
    command: LivestatusCommand,
    start_time: dt.datetime,
    end_time: dt.datetime,
    recur: RecurMode = 'fixed',
    trigger_id: int = 0,
    duration: int = 0,
    user_id: str = "",
    comment: str = "",
):
    """Unified low level function

    See:
     * schedule_host_downtime
     * schedule_service_downtime
    """
    # TODO: provide reference documents for recurring magic numbers
    # For more details have a look at:
    # https://assets.nagios.com/downloads/nagioscore/docs/externalcmds/cmdinfo.php?command_id=118

    recur_mode = _recur_to_even_mode(recur)

    if duration:
        # When a duration is set then the mode shifts to the next one. Even numbers (incl 0) signal
        # fixed recurring modes, odd numbers ones with a duration.
        recur_mode += 1

    return send_command(
        sites,
        command,
        [
            to_timestamp(start_time),
            to_timestamp(end_time),
            recur_mode,
            trigger_id,
            duration,
            user_id,
            comment.replace("\n", ""),
        ],
    )


def _recur_to_even_mode(recur: RecurMode) -> int:
    """Translate the recur-mode to livestatus' internally used magic-numbers.

    The numbers are defined like this:
        0: fixed between `start_time` and `end_time`
        1: starts between `start_time` and  `end_time` and lasts for `duration`
        2: repeats every hour
        3: repeats every hour (takes duration)
        4: repeats every day
        5: repeats every day (takes duration)
        6: repeats every week
        7: repeats every week (takes duration)
        8: repeats every second week
        9: repeats every second week (takes duration)
       10: repeats every fourth week
       11: repeats every fourth week (takes duration)
       12: repeats on same weekday as `start_date`
       13: (undefined?)
       14: repeats on same weekday as `end_date`
       15: (undefined?)
       16: repeats on the same day of the month as ??? (start_date or end_date?)
       17: (undefined?)

    """
    mapping: Dict[str, int] = {
        'fixed': 0,
        'hour': 2,
        'day': 4,
        'week': 6,
        'second_week': 8,
        'fourth_week': 10,
        'weekday_start': 12,
        'weekday_end': 14,
        'day_of_month': 16,
    }
    rv = mapping[recur]
    assert rv % 2 == 0, "Number is not even."  # This is intentional.
    return rv
