#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains commands for managing downtimes through LiveStatus."""
import datetime as dt
from typing import Dict, List, Literal, Optional, Union

from livestatus import SiteId

from cmk.utils.livestatus_helpers import tables
from cmk.utils.livestatus_helpers.expressions import Or, QueryExpression
from cmk.utils.livestatus_helpers.queries import detailed_connection, Query
from cmk.utils.livestatus_helpers.tables.downtimes import Downtimes
from cmk.utils.livestatus_helpers.tables.hosts import Hosts
from cmk.utils.livestatus_helpers.tables.services import Services

from cmk.gui.globals import user as _user
from cmk.gui.livestatus_utils.commands.lowlevel import send_command
from cmk.gui.livestatus_utils.commands.type_defs import LivestatusCommand
from cmk.gui.livestatus_utils.commands.utils import to_timestamp

# TODO: Test duration option

RecurMode = Literal[
    "fixed",  # TODO: Rename to "non_recurring"
    "hour",
    "day",
    "week",
    "second_week",
    "fourth_week",
    "weekday_start",
    "weekday_end",
    "day_of_month",
]


class QueryException(Exception):
    pass


def del_host_downtime(
    connection,
    downtime_id: int,
    site_id: SiteId,
):
    """Delete a host downtime.

    Args:
        connection:
            A livestatus connection object.

        downtime_id:
            The downtime-id.

        site_id:
            Id of site where command should be executed.

    Examples:

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.config import load_config
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.utils.logged_in import SuperUserContext

        >>> expect = simple_expect("COMMAND [...] DEL_HOST_DOWNTIME;1", match_type="ellipsis")
        >>> with expect as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     del_host_downtime(live, 1, "")

    """
    _user.need_permission("action.downtimes")

    return send_command(connection, "DEL_HOST_DOWNTIME", [downtime_id], site_id)


def del_service_downtime(
    connection,
    downtime_id: int,
    site_id: SiteId,
):
    """Delete a service downtime.

    Args:
        connection:
            A livestatus connection object.

        downtime_id:
            The downtime-id.

        site_id:
            Id of site where command should be executed.

    Examples:

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.config import load_config
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.utils.logged_in import SuperUserContext

        >>> expect = simple_expect("COMMAND [...] DEL_SVC_DOWNTIME;1", match_type="ellipsis")
        >>> with expect as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     del_service_downtime(live, 1, "")

    """
    _user.need_permission("action.downtimes")

    return send_command(connection, "DEL_SVC_DOWNTIME", [downtime_id], site_id)


def delete_downtime_with_query(connection, query):
    """Delete scheduled downtimes based upon a query"""
    q = Query([Downtimes.id, Downtimes.is_service]).filter(query)

    with detailed_connection(connection) as conn:
        downtimes = [(row["site"], row["id"], row["is_service"]) for row in q.iterate(conn)]

    for site_id, downtime_id, is_service in downtimes:
        if is_service:
            del_service_downtime(connection, downtime_id, site_id)
        else:
            del_host_downtime(connection, downtime_id, site_id)


def delete_downtime(connection, downtime_id):
    """Delete a scheduled downtime based upon the downtime id"""
    with detailed_connection(connection) as conn:
        entry = Query(
            [Downtimes.is_service],
            Downtimes.id == downtime_id,
        ).fetchone(conn)
    if entry["is_service"]:
        del_service_downtime(connection, downtime_id, entry["site"])
    else:
        del_host_downtime(connection, downtime_id, entry["site"])


def schedule_services_downtimes_with_query(
    connection,
    query: QueryExpression,
    start_time: dt.datetime,
    end_time: dt.datetime,
    recur: RecurMode = "fixed",
    duration: int = 0,
    user_id: str = "",
    comment: str = "",
):
    """Schedule downtimes for services based upon a query"""

    q = Query(
        [Services.description, Services.host_name],
        query,
    )
    with detailed_connection(connection) as conn:
        result = [(row["site"], row["host_name"], row["description"]) for row in q.iterate(conn)]

    if not result:
        raise QueryException

    for site_id, host_name, service_description in result:
        if not comment:
            downtime_comment = f"Downtime for service {service_description}@{host_name}"
        else:
            downtime_comment = comment

        schedule_service_downtime(
            connection,
            site_id=site_id,
            host_name=host_name,
            service_description=service_description,
            start_time=start_time,
            end_time=end_time,
            recur=recur,
            duration=duration,
            user_id=user_id,
            comment=downtime_comment,
        )


def schedule_service_downtime(
    connection,
    site_id: SiteId,
    host_name: str,
    service_description: Union[List[str], str],
    start_time: dt.datetime,
    end_time: dt.datetime,
    recur: RecurMode = "fixed",
    trigger_id: int = 0,
    duration: int = 0,
    user_id: str = "",
    comment: str = "",
):
    """Schedule the downtime of a host.

    Args:
        connection:
            A livestatus connection object.

        host_name:
            The host-name for which this downtime is for.

        service_description:
            The service description of the service, whose problems shall be acknowledged.

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

            This only works when using the Enterprise Editions.

        trigger_id:
            The id of another downtime-entry. If given (other than 0) then this downtime will be
            triggered by the other downtime.

        duration:
            Duration in seconds. When set, the downtime does not begin automatically at a nominated
            time, but when a real problem status appears for the service. Consequencely, the
            start_time/end_time is only the time window in which the scheduled downtime can begin.

        user_id:

        comment:
            A comment which will be added to the downtime.

        site_id:
            Site which is targeted by command

    See Also:
        https://assets.nagios.com/downloads/nagioscore/docs/externalcmds/cmdinfo.php?command_id=119

    Examples:

        >>> import pytz
        >>> _start_time = dt.datetime(1970, 1, 1, tzinfo=pytz.timezone("UTC"))
        >>> _end_time = dt.datetime(1970, 1, 2, tzinfo=pytz.timezone("UTC"))

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.config import load_config
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.utils.logged_in import SuperUserContext

        >>> cmd = "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;0;86400;16;0;120;;Boom"
        >>> with simple_expect() as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     _ = live.expect_query(cmd, match_type="ellipsis")
        ...     schedule_service_downtime(live,
        ...             SiteId('NO_SITE'),
        ...             'example.com',
        ...             'Memory',
        ...             _start_time,
        ...             _end_time,
        ...             recur="day_of_month",
        ...             duration=120,
        ...             comment="Boom")

    """
    if isinstance(service_description, str):
        service_descriptions = [service_description]
    else:
        service_descriptions = service_description

    for _service_description in service_descriptions:
        _schedule_downtime(
            connection,
            "SCHEDULE_SVC_DOWNTIME",
            site_id,
            host_name,
            _service_description,
            start_time,
            end_time,
            recur,
            trigger_id,
            duration,
            user_id,
            comment,
        )


def schedule_servicegroup_service_downtime(
    connection,
    servicegroup_name: str,
    start_time: dt.datetime,
    end_time: dt.datetime,
    include_hosts: bool = False,
    recur: RecurMode = "fixed",
    trigger_id: int = 0,
    duration: int = 0,
    user_id: str = "",
    comment: str = "",
):
    """Schedules downtime for all hosts, which have services in a given service group.

    Args:
        connection:
            A LiveStatus connection object.

        servicegroup_name:
            The name of the service group. Any host having a service in this group will be
            A downtime will be scheduled for all hosts in this group.

        start_time:
            When the downtime shall begin.

        end_time:
            When the downtime shall end.

        include_hosts:
            When set to True, all hosts will also receive a scheduled downtime, not just their
            services which belong to this service group.

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

            This only works when using the Enterprise Editions. Defaults to 'fixed'.

        trigger_id:
            The id of another downtime-entry. If given (other than 0) then this downtime will be
            triggered by the other downtime.

        duration:
            Duration in seconds. When set, the downtime does not begin automatically at a nominated
            time, but when a real problem status appears for the host. Consequently, the
            start_time/end_time is only the time window in which the scheduled downtime can begin.

        user_id:

        comment:
            A comment which will be added to the downtime.

        connection:

    """
    with detailed_connection(connection) as conn:
        entries = list(
            Query(
                [tables.Servicegroups.members],
                tables.Servicegroups.name.equals(servicegroup_name),
            ).iterate(conn)
        )
    for entry in entries:
        site = entry["site"]
        for host_name, service_description in entry["members"]:
            schedule_service_downtime(
                connection,
                site,
                host_name=host_name,
                service_description=service_description,
                start_time=start_time,
                end_time=end_time,
                recur=recur,
                trigger_id=trigger_id,
                duration=duration,
                user_id=user_id,
                comment=comment,
            )

    if include_hosts:
        host_names = _deduplicate([host for entry in entries for (host, _) in entry["members"]])
        schedule_host_downtime(
            connection,
            host_entry=host_names,
            start_time=start_time,
            end_time=end_time,
            recur=recur,
            trigger_id=trigger_id,
            duration=duration,
            user_id=user_id,
            comment=comment,
        )


def schedule_hostgroup_host_downtime(
    connection,
    hostgroup_name: str,
    start_time: dt.datetime,
    end_time: dt.datetime,
    include_all_services: bool = False,
    recur: RecurMode = "fixed",
    trigger_id: int = 0,
    duration: int = 0,
    user_id: str = "",
    comment: str = "",
):
    """Schedules downtime for all hosts in a given host group.

    Args:
        connection:
            A LiveStatus connection object.

        hostgroup_name:
            The name of the host group. A downtime will be scheduled for all hosts in this host group.

        start_time:
            When the downtime shall begin.

        end_time:
            When the downtime shall end.

        include_all_services:
            If set, downtimes for all services associated with the given host will be scheduled.
            Defaults to False.

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

            This only works when using the Enterprise Editions. Defaults to 'fixed'.

        trigger_id:
            The id of another downtime-entry. If given (other than 0) then this downtime will be
            triggered by the other downtime.

        duration:
            Duration in seconds. When set, the downtime does not begin automatically at a nominated
            time, but when a real problem status appears for the host. Consequently, the
            start_time/end_time is only the time window in which the scheduled downtime can begin.

        user_id:

        comment:
            A comment which will be added to the downtime.

        connection:

    See Also:
      * https://assets.nagios.com/downloads/nagioscore/docs/externalcmds/cmdinfo.php?command_id=123

    """
    result = Query(
        [tables.Hostgroups.members], tables.Hostgroups.name.equals(hostgroup_name)
    ).iterate(connection)

    hosts = [host for entry in result for host in entry["members"]]
    schedule_host_downtime(
        connection,
        host_entry=hosts,
        start_time=start_time,
        end_time=end_time,
        include_all_services=include_all_services,
        recur=recur,
        trigger_id=trigger_id,
        duration=duration,
        user_id=user_id,
        comment=comment,
    )


def schedule_hosts_downtimes_with_query(
    connection,
    query: QueryExpression,
    start_time: dt.datetime,
    end_time: dt.datetime,
    include_all_services=False,
    recur: RecurMode = "fixed",
    duration: int = 0,
    user_id: str = "",
    comment: str = "",
):
    """Schedule a downtimes for hosts based upon a query"""

    q = Query([Hosts.name]).filter(query)

    hosts = [row["name"] for row in q.iterate(connection)]

    if not hosts:
        raise QueryException

    if not comment:
        comment = f"Downtime for hosts {', '.join([entry[1] for entry in hosts])}"

    schedule_host_downtime(
        connection,
        host_entry=hosts,
        start_time=start_time,
        end_time=end_time,
        include_all_services=include_all_services,
        recur=recur,
        duration=duration,
        user_id=user_id,
        comment=comment,
    )


def schedule_host_downtime(
    connection,
    host_entry: Union[str, List[str]],
    start_time: dt.datetime,
    end_time: dt.datetime,
    include_all_services: bool = False,
    recur: RecurMode = "fixed",
    trigger_id: int = 0,
    duration: int = 0,
    user_id: str = "",
    comment: str = "",
):
    """Schedule the downtime of a host.

    Notes:
        If `include_all_services` is set to True, the services table is only queried
        once, instead of len(host_name) times. If a lot of hosts are to be scheduled, this
        will save N queries. Issuing the command is still done sequentially.

    Args:
        connection:
            A livestatus connection object.

        host_entry:
            The host-name for which this downtime is for.

        start_time:
            When the downtime shall begin.

        end_time:
            When the downtime shall end.

        include_all_services:
            If set, downtimes for all services associated with the given host will be scheduled.
            Defaults to False.

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

            This only works when using the Enterprise Editions. Defaults to 'fixed'.

        trigger_id:
            The id of another downtime-entry. If given (other than 0) then this downtime will be
            triggered by the other downtime.

        duration:
            Duration in seconds. When set, the downtime does not begin automatically at a nominated
            time, but when a real problem status appears for the host. Consequencely, the
            start_time/end_time is only the time window in which the scheduled downtime can begin.

        user_id:

        comment:
            A comment which will be added to the downtime.

    See Also:
      * https://assets.nagios.com/downloads/nagioscore/docs/externalcmds/cmdinfo.php?command_id=118
      * https://assets.nagios.com/downloads/nagioscore/docs/externalcmds/cmdinfo.php?command_id=122

    Examples:
        >>> import pytz
        >>> _start_time = dt.datetime(1970, 1, 1, tzinfo=pytz.timezone("UTC"))
        >>> _end_time = dt.datetime(1970, 1, 2, tzinfo=pytz.timezone("UTC"))

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.config import load_config
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.utils.logged_in import SuperUserContext

        >>> cmd = "COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;16;0;120;;Boom"
        >>> with simple_expect() as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     _ = live.expect_query("GET hosts\\nColumns: name\\nFilter: name = example.com")
        ...     _ = live.expect_query(cmd, match_type="ellipsis")
        ...     schedule_host_downtime(live,
        ...             'example.com',
        ...             _start_time,
        ...             _end_time,
        ...             recur="day_of_month",
        ...             duration=120,
        ...             comment="Boom")

    """
    if isinstance(host_entry, str):
        hosts = [host_entry]
    elif host_entry:
        hosts = host_entry
    else:
        raise ValueError("List of hosts may not be empty.")

    with detailed_connection(connection) as conn:
        host_entries = [
            (entry["site"], entry["name"])
            for entry in Query(
                [Hosts.name], Or(*[Hosts.name.equals(host) for host in hosts])
            ).fetchall(conn)
        ]

    for _site, _host_name in host_entries:
        _schedule_downtime(
            connection,
            "SCHEDULE_HOST_DOWNTIME",
            _site,
            _host_name,
            None,
            start_time,
            end_time,
            recur,
            trigger_id,
            duration,
            user_id,
            comment,
        )

    if include_all_services:
        with detailed_connection(connection) as conn:
            services = Query(
                [tables.Services.host_name, tables.Services.description],
                Or(
                    *[
                        tables.Services.host_name.equals(_host_name)
                        for _, _host_name in host_entries
                    ]
                ),
            ).fetch_values(conn)

        for _site, _host_name, service_description in services:
            schedule_service_downtime(
                connection,
                _site,
                host_name=_host_name,
                service_description=service_description,
                start_time=start_time,
                end_time=end_time,
                recur=recur,
                trigger_id=trigger_id,
                duration=duration,
                user_id=user_id,
                comment=comment,
            )


def _schedule_downtime(
    sites,
    command: LivestatusCommand,
    site_id,
    host_or_group: str,
    service_description: Optional[str],
    start_time: dt.datetime,
    end_time: dt.datetime,
    recur: RecurMode = "fixed",
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
    _user.need_permission("action.downtimes")

    recur_mode = _recur_mode(recur, duration)

    if command == "SCHEDULE_HOST_DOWNTIME":
        params = [host_or_group]
    elif command == "SCHEDULE_SVC_DOWNTIME":
        if not service_description:
            raise ValueError("Service description necessary.")
        params = [host_or_group, service_description]
    else:
        raise ValueError(f"Unsupported command: {command}")

    return send_command(
        sites,
        command,
        [
            *params,
            to_timestamp(start_time),
            to_timestamp(end_time),
            recur_mode,
            trigger_id,
            duration,
            user_id,
            comment.replace("\n", ""),
        ],
        site_id,
    )


def _recur_mode(recur: RecurMode, duration: int) -> int:
    """Translate the recur-mode to livestatus' internally used magic-numbers.

    The numbers are defined like this:
        0: starts between `start_time` and  `end_time` and lasts for `duration`
        1: fixed between `start_time` and `end_time`
        2: repeats every hour (takes duration)
        3: repeats every hour
        4: repeats every day (takes duration)
        5: repeats every day
        6: repeats every week (takes duration)
        7: repeats every week
        8: repeats every second week (takes duration)
        9: repeats every second week
       10: repeats every fourth week (takes duration)
       11: repeats every fourth week
       12: (undefined?)
       13: repeats on same weekday as `start_date`
       14: (undefined?)
       15: repeats on same weekday as `end_date`
       16: (undefined?)
       17: repeats on the same day of the month as ??? (start_date or end_date?)

    Examples:

        We don't test the KeyError case as it's supposed to be one execution path and mypy will
        check for the input.

        >>> _recur_mode('fixed', 0)
        1

        >>> _recur_mode('fixed', 30)
        0

        >>> _recur_mode('second_week', 0)
        9

    """
    mapping: Dict[str, int] = {
        "fixed": 0,
        "hour": 2,
        "day": 4,
        "week": 6,
        "second_week": 8,
        "fourth_week": 10,
        "weekday_start": 12,
        "weekday_end": 14,
        "day_of_month": 16,
    }
    rv = mapping[recur]
    assert rv % 2 == 0, "Number is not even."  # This is intentional.

    if not duration:
        # When a duration is not set then the mode shifts to the next one. Even numbers (incl 0)
        # signal recurring modes with a duration, odd numbers signal fixed ones.
        rv += 1

    return rv


# not type checked due to mypy restrictions. this could be anything hashable but you can't type it
# correctly. :-/
def _deduplicate(seq):
    """Like set() but retains sorting order of input.

    Args:
        seq:
            Any sequence with hashable contents.

    Returns:
        Deduplicated sequence. The first entry of duplications is kept, any repeating entries
        are discarded.

    Examples:

        >>> _deduplicate([1, 1, 2, 1, 3, 4, 5, 1, 2, 3, 6, 1])
        [1, 2, 3, 4, 5, 6]

        >>> _deduplicate((1, 1, 2, 1, 3, 4, 5, 1, 2, 3, 6, 1))
        [1, 2, 3, 4, 5, 6]

        >>> _deduplicate(['Hello', 'Hello', 'World', 'World', 'World', '!', '!', '!'])
        ['Hello', 'World', '!']

    """
    result = []
    seen = set()
    for entry in seq:
        if entry in seen:
            continue
        seen.add(entry)
        result.append(entry)

    return result
