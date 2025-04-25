#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains commands for managing downtimes through LiveStatus."""

import datetime as dt
from typing import Literal

from livestatus import MultiSiteConnection

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

from cmk.utils.livestatus_helpers import tables
from cmk.utils.livestatus_helpers.expressions import And, Or, QueryExpression
from cmk.utils.livestatus_helpers.queries import detailed_connection, Query
from cmk.utils.livestatus_helpers.tables.downtimes import Downtimes
from cmk.utils.livestatus_helpers.tables.hosts import Hosts
from cmk.utils.livestatus_helpers.tables.services import Services

from cmk.gui.exceptions import MKAuthException
from cmk.gui.livestatus_utils.commands.lowlevel import send_command
from cmk.gui.livestatus_utils.commands.type_defs import LivestatusCommand
from cmk.gui.livestatus_utils.commands.utils import to_timestamp
from cmk.gui.logged_in import user as _user

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


class DOWNTIME:
    SCHEDULE_HOST: LivestatusCommand = "SCHEDULE_HOST_DOWNTIME"
    SCHEDULE_SERVICE: LivestatusCommand = "SCHEDULE_SVC_DOWNTIME"
    DELETE_HOST: LivestatusCommand = "DEL_HOST_DOWNTIME"
    DELETE_SERVICE: LivestatusCommand = "DEL_SVC_DOWNTIME"
    MODIFY_HOST: LivestatusCommand = "MODIFY_HOST_DOWNTIME"
    MODIFY_SERVICE: LivestatusCommand = "MODIFY_SVC_DOWNTIME"


class QueryException(Exception):
    pass


def _del_host_downtime(
    connection: MultiSiteConnection,
    downtime_id: int,
    site_id: SiteId | None,
) -> None:
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
        >>> from cmk.gui.session import SuperUserContext

        >>> expect = simple_expect("COMMAND [...] DEL_HOST_DOWNTIME;1", match_type="ellipsis")
        >>> with expect as live, SuperUserContext():
        ...     load_config()
        ...     _del_host_downtime(live, 1, "")

    """

    return send_command(connection, DOWNTIME.DELETE_HOST, [downtime_id], site_id)


def _del_service_downtime(
    connection: MultiSiteConnection,
    downtime_id: int,
    site_id: SiteId | None,
) -> None:
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
        >>> from cmk.gui.session import SuperUserContext

        >>> expect = simple_expect("COMMAND [...] DEL_SVC_DOWNTIME;1", match_type="ellipsis")
        >>> with expect as live, SuperUserContext():
        ...     load_config()
        ...     _del_service_downtime(live, 1, "")

    """

    return send_command(connection, DOWNTIME.DELETE_SERVICE, [downtime_id], site_id)


def delete_downtime(
    connection: MultiSiteConnection,
    query: QueryExpression,
    site_id: SiteId | None,
) -> None:
    """Delete a scheduled downtime"""
    _user.need_permission("action.downtimes")

    only_sites = None if site_id is None else [site_id]
    downtimes = Query(
        [Downtimes.id, Downtimes.is_service],
        query,
    ).fetchall(connection, True, only_sites)

    for downtime in downtimes:
        if downtime["is_service"]:
            _del_service_downtime(connection, downtime["id"], downtime["site"])
        else:
            _del_host_downtime(connection, downtime["id"], downtime["site"])


def modify_downtimes(
    connection: MultiSiteConnection,
    query: QueryExpression,
    site_id: SiteId | None,
    end_time: str | None = None,
    comment: str | None = None,
    user_id: UserId = UserId.builtin(),
) -> None:
    """Update scheduled downtimes"""

    only_sites = None if site_id is None else [site_id]
    downtimes = Query(
        [
            Downtimes.id,
            Downtimes.is_service,
        ],
        query,
    ).fetchall(connection, True, only_sites)

    for downtime in downtimes:
        command = DOWNTIME.MODIFY_SERVICE if downtime["is_service"] else DOWNTIME.MODIFY_HOST
        _modify_downtime(
            connection,
            command,
            downtime["id"],
            downtime["site"],
            end_time="" if end_time is None else end_time,
            comment=comment if comment is not None else "",
            user_id=user_id,
        )


def schedule_services_downtimes_with_query(
    connection: MultiSiteConnection,
    query: QueryExpression,
    start_time: dt.datetime,
    end_time: dt.datetime,
    recur: RecurMode = "fixed",
    duration: int = 0,
    user_id: UserId = UserId.builtin(),
    comment: str = "",
) -> None:
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

        _schedule_downtime(
            sites=connection,
            command=DOWNTIME.SCHEDULE_SERVICE,
            site_id=site_id,
            host_or_group=host_name,
            service_description=service_description,
            start_time=start_time,
            end_time=end_time,
            recur=recur,
            duration=duration,
            user_id=user_id,
            comment=downtime_comment,
        )


def schedule_service_downtime(
    connection: MultiSiteConnection,
    site_id: SiteId | None,
    host_name: str,
    service_description: list[str] | str,
    start_time: dt.datetime,
    end_time: dt.datetime,
    recur: RecurMode = "fixed",
    trigger_id: int = 0,
    duration: int = 0,
    user_id: UserId = UserId.builtin(),
    comment: str = "",
) -> None:
    """Schedule the downtime of a host.

    Args:
        connection:
            A livestatus connection object.

        host_name:
            The host-name for which this downtime is for.

        service_description:
            The service name of the service, whose problems shall be acknowledged.

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
            Duration in minutes. When set, the downtime does not begin automatically at a nominated
            time, but when a real problem status appears for the service. Consequencely, the
            start_time/end_time is only the time window in which the scheduled downtime can begin.

        user_id:

        comment:
            A comment which will be added to the downtime.

        site_id:
            An optional Site which is targeted by the command. Defaults to the local site if 'None'.

    See Also:
        https://assets.nagios.com/downloads/nagioscore/docs/externalcmds/cmdinfo.php?command_id=119

    Examples:

        >>> from zoneinfo import ZoneInfo
        >>> _start_time = dt.datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))
        >>> _end_time = dt.datetime(1970, 1, 2, tzinfo=ZoneInfo("UTC"))

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.config import load_config
        >>> from cmk.gui.session import SuperUserContext

        >>> cmd = "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;0;86400;16;0;120;;Boom"
        >>> with simple_expect() as live, SuperUserContext():
        ...     load_config()
        ...     _ = live.expect_query("GET services\\nColumns: description\\nFilter: host_name = example.com\\nFilter: description = Memory\\nAnd: 2")
        ...     _ = live.expect_query(cmd, match_type="ellipsis")
        ...     schedule_service_downtime(live,
        ...             SiteId('NO_SITE'),
        ...             'example.com',
        ...             'Memory',
        ...             _start_time,
        ...             _end_time,
        ...             recur="day_of_month",
        ...             duration=2,
        ...             comment="Boom")

    """

    with detailed_connection(connection) as conn:
        service_entries = Query(
            [Services.description],
            And(
                Services.host_name.equals(host_name),
                Or(
                    *[
                        Services.description.equals(desc)
                        for desc in (
                            [service_description]
                            if isinstance(service_description, str)
                            else service_description
                        )
                    ]
                ),
            ),
        ).fetchall(conn)

    if not service_entries:
        raise MKAuthException(f"Cannot find the requested resource: {service_description}")

    for row in service_entries:
        _schedule_downtime(
            sites=connection,
            command=DOWNTIME.SCHEDULE_SERVICE,
            site_id=site_id,
            host_or_group=host_name,
            service_description=row[Services.description.name],
            start_time=start_time,
            end_time=end_time,
            recur=recur,
            trigger_id=trigger_id,
            duration=duration,
            user_id=user_id,
            comment=comment,
        )


def schedule_servicegroup_service_downtime(
    connection: MultiSiteConnection,
    servicegroup_name: str,
    start_time: dt.datetime,
    end_time: dt.datetime,
    include_hosts: bool = False,
    recur: RecurMode = "fixed",
    trigger_id: int = 0,
    duration: int = 0,
    user_id: UserId = UserId.builtin(),
    comment: str = "",
) -> None:
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
            Duration in minutes. When set, the downtime does not begin automatically at a nominated
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

    if not entries:
        raise MKAuthException(f"Cannot find services for service group: {servicegroup_name}")

    included_hosts = set()

    for entry in entries:
        site = entry["site"]
        for host_name, service_description in entry["members"]:
            _schedule_downtime(
                sites=connection,
                command=DOWNTIME.SCHEDULE_SERVICE,
                site_id=site,
                host_or_group=host_name,
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
                included_hosts.add((site, host_name))

    for site, host_name in included_hosts:
        _schedule_downtime(
            sites=connection,
            command=DOWNTIME.SCHEDULE_HOST,
            site_id=site,
            host_or_group=host_name,
            service_description=None,
            start_time=start_time,
            end_time=end_time,
            recur=recur,
            trigger_id=trigger_id,
            duration=duration,
            user_id=user_id,
            comment=comment,
        )


def schedule_hostgroup_host_downtime(
    connection: MultiSiteConnection,
    hostgroup_name: str,
    start_time: dt.datetime,
    end_time: dt.datetime,
    include_all_services: bool = False,
    recur: RecurMode = "fixed",
    trigger_id: int = 0,
    duration: int = 0,
    user_id: UserId = UserId.builtin(),
    comment: str = "",
) -> None:
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
            Duration in minutes. When set, the downtime does not begin automatically at a nominated
            time, but when a real problem status appears for the host. Consequently, the
            start_time/end_time is only the time window in which the scheduled downtime can begin.

        user_id:

        comment:
            A comment which will be added to the downtime.

        connection:

    See Also:
      * https://assets.nagios.com/downloads/nagioscore/docs/externalcmds/cmdinfo.php?command_id=123

    """

    with detailed_connection(connection) as conn:
        result = list(
            Query(
                [tables.Hostgroups.members], tables.Hostgroups.name.equals(hostgroup_name)
            ).fetchall(conn)
        )

    if not result:
        raise MKAuthException(f"Cannot find hosts for host group: {hostgroup_name}")

    for entry in result:
        site = entry["site"]
        for host in entry["members"]:
            _schedule_downtime(
                sites=connection,
                command=DOWNTIME.SCHEDULE_HOST,
                site_id=site,
                host_or_group=host,
                service_description=None,
                start_time=start_time,
                end_time=end_time,
                recur=recur,
                trigger_id=trigger_id,
                duration=duration,
                user_id=user_id,
                comment=comment,
            )

    if include_all_services:
        _schedule_service_downtime_for_hosts_services(
            connection=connection,
            host_entries=[host for entry in result for host in entry["members"]],
            start_time=start_time,
            end_time=end_time,
            recur=recur,
            trigger_id=trigger_id,
            duration=duration,
            user_id=user_id,
            comment=comment,
        )


def schedule_hosts_downtimes_with_query(
    connection: MultiSiteConnection,
    query: QueryExpression,
    start_time: dt.datetime,
    end_time: dt.datetime,
    include_all_services: bool = False,
    recur: RecurMode = "fixed",
    duration: int = 0,
    user_id: UserId = UserId.builtin(),
    comment: str = "",
) -> None:
    """Schedule a downtimes for hosts based upon a query"""

    with detailed_connection(connection) as conn:
        host_entries = [
            (entry["site"], entry["name"])
            for entry in Query([Hosts.name]).filter(query).fetchall(conn)
        ]

    if not host_entries:
        raise QueryException

    if not comment:
        comment = f"Downtime for hosts {', '.join([entry[1] for entry in host_entries])}"

    for site, host_name in host_entries:
        _schedule_downtime(
            sites=connection,
            command=DOWNTIME.SCHEDULE_HOST,
            site_id=site,
            host_or_group=host_name,
            service_description=None,
            start_time=start_time,
            end_time=end_time,
            recur=recur,
            duration=duration,
            user_id=user_id,
            comment=comment,
        )

    if include_all_services:
        _schedule_service_downtime_for_hosts_services(
            connection=connection,
            host_entries=[entry[1] for entry in host_entries],
            start_time=start_time,
            end_time=end_time,
            recur=recur,
            duration=duration,
            user_id=user_id,
            comment=comment,
        )


def schedule_host_downtime(
    connection: MultiSiteConnection,
    host_entry: str | list[str],
    start_time: dt.datetime,
    end_time: dt.datetime,
    include_all_services: bool = False,
    recur: RecurMode = "fixed",
    trigger_id: int = 0,
    duration: int = 0,
    user_id: UserId = UserId.builtin(),
    comment: str = "",
) -> None:
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
            Duration in minutes. When set, the downtime does not begin automatically at a nominated
            time, but when a real problem status appears for the host. Consequencely, the
            start_time/end_time is only the time window in which the scheduled downtime can begin.

        user_id:

        comment:
            A comment which will be added to the downtime.

    See Also:
      * https://assets.nagios.com/downloads/nagioscore/docs/externalcmds/cmdinfo.php?command_id=118
      * https://assets.nagios.com/downloads/nagioscore/docs/externalcmds/cmdinfo.php?command_id=122

    Examples:
        >>> from zoneinfo import ZoneInfo
        >>> _start_time = dt.datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))
        >>> _end_time = dt.datetime(1970, 1, 2, tzinfo=ZoneInfo("UTC"))

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.config import load_config
        >>> from cmk.gui.session import SuperUserContext

        >>> cmd = "COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;16;0;120;;Boom"
        >>> with simple_expect() as live, SuperUserContext():
        ...     load_config()
        ...     _ = live.expect_query("GET hosts\\nColumns: name\\nFilter: name = example.com")
        ...     _ = live.expect_query(cmd, match_type="ellipsis")
        ...     schedule_host_downtime(live,
        ...             'example.com',
        ...             _start_time,
        ...             _end_time,
        ...             recur="day_of_month",
        ...             duration=2,
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

    if not host_entries:
        raise MKAuthException(f"Cannot find the requested resource: {host_entry}")

    for site, host_name in host_entries:
        _schedule_downtime(
            sites=connection,
            command=DOWNTIME.SCHEDULE_HOST,
            site_id=site,
            host_or_group=host_name,
            service_description=None,
            start_time=start_time,
            end_time=end_time,
            recur=recur,
            trigger_id=trigger_id,
            duration=duration,
            user_id=user_id,
            comment=comment,
        )

    if include_all_services:
        _schedule_service_downtime_for_hosts_services(
            connection=connection,
            host_entries=[_host_name for _site, _host_name in host_entries],
            start_time=start_time,
            end_time=end_time,
            recur=recur,
            trigger_id=trigger_id,
            duration=duration,
            user_id=user_id,
            comment=comment,
        )


def _schedule_service_downtime_for_hosts_services(
    connection: MultiSiteConnection,
    host_entries: list[str],
    start_time: dt.datetime,
    end_time: dt.datetime,
    recur: RecurMode = "fixed",
    trigger_id: int = 0,
    duration: int = 0,
    user_id: UserId = UserId.builtin(),
    comment: str = "",
) -> None:
    with detailed_connection(connection) as conn:
        services = Query(
            [tables.Services.host_name, tables.Services.description],
            Or(*[tables.Services.host_name.equals(_host_name) for _host_name in host_entries]),
        ).fetch_values(conn)

    for site, host_name, service_description in services:
        _schedule_downtime(
            sites=connection,
            command=DOWNTIME.SCHEDULE_SERVICE,
            site_id=site,
            host_or_group=host_name,
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
    sites: MultiSiteConnection,
    command: LivestatusCommand,
    site_id: SiteId | None,
    host_or_group: str,
    service_description: str | None,
    start_time: dt.datetime,
    end_time: dt.datetime,
    recur: RecurMode = "fixed",
    trigger_id: int = 0,
    duration: int = 0,
    user_id: UserId = UserId.builtin(),
    comment: str = "",
) -> None:
    """Unified low level function

    See:
     * schedule_host_downtime
     * schedule_service_downtime
    """
    # TODO: provide reference documents for recurring magic numbers
    _user.need_permission("action.downtimes")

    recur_mode = _recur_mode(recur, duration)

    if command == DOWNTIME.SCHEDULE_HOST:
        params = [host_or_group]
    elif command == DOWNTIME.SCHEDULE_SERVICE:
        if not service_description:
            raise ValueError("Service name necessary.")
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
            60 * duration,  # duration is in minutes but livestatus is expecting seconds.,
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
    mapping: dict[str, int] = {
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


def _modify_downtime(
    sites: MultiSiteConnection,
    command: LivestatusCommand,
    downtime_id: int,
    site_id: SiteId | None,
    end_time: str = "",
    comment: str = "",
    user_id: UserId = UserId.builtin(),
) -> None:
    _user.need_permission("action.downtimes")

    return send_command(
        sites,
        command,
        [
            downtime_id,
            "",  # start_time (not used),
            end_time,  # end_time,
            "",  # recur_mode (not used),
            "",  # trigger_id (not used),
            "",  # duration (not used),
            user_id,
            comment.replace("\n", ""),
        ],
        site_id,
    )
