#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains helpers to trigger acknowledgments."""

import datetime as dt

from livestatus import MultiSiteConnection

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

from cmk.utils.livestatus_helpers import tables
from cmk.utils.livestatus_helpers.queries import detailed_connection, Query
from cmk.utils.livestatus_helpers.tables import Hosts

from cmk.gui.livestatus_utils.commands.downtimes import QueryException
from cmk.gui.livestatus_utils.commands.lowlevel import send_command
from cmk.gui.livestatus_utils.commands.type_defs import LivestatusCommand
from cmk.gui.logged_in import user as _user


def _acknowledge_problem(
    connection: MultiSiteConnection,
    site_id: SiteId,
    host_name: str,
    service_description: str | None = None,
    *,
    sticky: bool = False,
    notify: bool = False,
    persistent: bool = False,
    user: UserId = UserId.builtin(),
    comment: str = "",
    expire_on: dt.datetime | None = None,
) -> None:
    """Acknowledge a problem for a host or service.

    Args:
        connection: A livestatus connection object.
        site_id: Site ID of the host or service.
        host_name: Host name for which this acknowledgement is for.
        service_description: Service name, if acknowledging a service problem.
        sticky: If set, only a state-change to the UP/OK state will discard the acknowledgement.
                Otherwise, it will be discarded on any state-change.
        notify: If set, notifications will be sent out to the configured contacts.
        persistent: If set, the comment will persist a restart.
        user: User ID of the user who acknowledged the problem.
        comment: Comment to be stored alongside the acknowledgement.
        expire_on: If set, the acknowledgement will expire at this time.
    """
    params: list[str | int] = [
        host_name,
    ]
    if service_description:
        command: LivestatusCommand = "ACKNOWLEDGE_SVC_PROBLEM"
        params.append(service_description)
    else:
        command = "ACKNOWLEDGE_HOST_PROBLEM"

    acknowledgement = 2 if sticky else 1  # 1: normal, 2: sticky
    params.extend(
        (
            acknowledgement,
            int(notify),
            int(persistent),
            user,
            comment,
        )
    )
    if expire_on is not None:
        params.append(int(expire_on.timestamp()))

    return send_command(
        connection,
        command,
        params,
        site_id=site_id,
    )


def remove_acknowledgement(
    connection: MultiSiteConnection,
    site_id: SiteId,
    host_name: str,
    service_description: str | None = None,
) -> None:
    """Remove an acknowledgement for a host or service problem.

    Args:
        connection: A livestatus connection object.
        site_id: Site ID of the host or service.
        host_name: Host name for which this acknowledgement is for.
        service_description: Service name, if acknowledging a service problem.
    """
    params: list[str | int] = [
        host_name,
    ]
    if service_description:
        command: LivestatusCommand = "REMOVE_SVC_ACKNOWLEDGEMENT"
        params.append(service_description)
    else:
        command = "REMOVE_HOST_ACKNOWLEDGEMENT"

    return send_command(
        connection,
        command,
        params,
        site_id=site_id,
    )


def acknowledge_service_problem(
    connection: MultiSiteConnection,
    host_name: str,
    service_description: str,
    sticky: bool = False,
    notify: bool = False,
    persistent: bool = False,
    user: UserId = UserId.builtin(),
    comment: str = "",
    expire_on: dt.datetime | None = None,
) -> None:
    """Acknowledge the current problem for the given service.

    When acknowledging a problem, further notifications for the service are disabled, as
    long as the service doesn't change state. At state change, notifications are re-enabled.

    Args:
        connection: A livestatus connection object.
        host_name: Host name for which this acknowledgement is for.
        service_description: Service name for which this acknowledgement is for.
        sticky: If set, only a state-change to the UP/OK state will discard the acknowledgement.
                Otherwise, it will be discarded on any state-change.
        notify: If set, notifications will be sent out to the configured contacts.
        persistent: If set, the comment will persist a restart.
        user: User ID of the user who acknowledged the problem.
        comment: Comment to be stored alongside the acknowledgement.
        expire_on: If set, the acknowledgement will expire at this time.

    Examples:

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.livestatus_utils.testing import mock_site

        >>> cmd = "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;drain;1;0;0;;"
        >>> with simple_expect() as live:
        ...     _ = live.expect_query("GET hosts\\nColumns: name\\nFilter: name = example.com")
        ...     _ = live.expect_query(cmd, match_type="ellipsis")
        ...     acknowledge_service_problem(live, 'example.com', 'drain')

        Not authenticated users can't call this function:

            >>> with mock_site(), application_and_request_context():
            ...     acknowledge_service_problem(live, 'example.com', 'drain')   # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKAuthException: ...
    """
    _user.need_permission("action.acknowledge")

    site_id = _query_site(connection, host_name)

    _acknowledge_problem(
        connection,
        site_id,
        host_name,
        service_description,
        sticky=sticky,
        notify=notify,
        persistent=persistent,
        user=user,
        comment=comment,
        expire_on=expire_on,
    )


def acknowledge_servicegroup_problem(
    connection: MultiSiteConnection,
    servicegroup_name: str,
    sticky: bool = False,
    notify: bool = False,
    persistent: bool = False,
    user: UserId = UserId.builtin(),
    comment: str = "",
    expire_on: dt.datetime | None = None,
) -> None:
    """Acknowledge the problems of the current services of the service group

    When acknowledging a problem, further notifications for the respective services are disabled, as
    long as a specific service doesn't change state. At state change, notifications are re-enabled.

    Args:
        connection: A livestatus connection object.
        servicegroup_name: Service group name for which this acknowledgement is for.
        sticky: If set, only a state-change to the UP/OK state will discard the acknowledgement.
                Otherwise, it will be discarded on any state-change.
        notify: If set, notifications will be sent out to the configured contacts.
        persistent: If set, the comment will persist a restart.
        user: User ID of the user who acknowledged the problem.
        comment: Comment to be stored alongside the acknowledgement.
        expire_on: If set, the acknowledgement will expire at this time.

    Raises:
        ValueError:
            When the service group could not be found.
    """
    _user.need_permission("action.acknowledge")

    with detailed_connection(connection) as conn:
        group_entries = Query(
            [tables.Servicegroups.members],
            tables.Servicegroups.name.equals(servicegroup_name),
        ).fetchall(conn)

    for entry in group_entries:
        site_id = entry["site"]
        for host_name, service_description in entry["members"]:
            _acknowledge_problem(
                connection,
                site_id,
                host_name,
                service_description,
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                user=user,
                comment=comment,
                expire_on=expire_on,
            )


def acknowledge_host_problem(
    connection: MultiSiteConnection,
    host_name: str,
    sticky: bool = False,
    notify: bool = False,
    persistent: bool = False,
    user: UserId = UserId.builtin(),
    comment: str = "",
    expire_on: dt.datetime | None = None,
) -> None:
    """Acknowledge the current problem for the given host.

    When acknowledging a problem, notifications for the host are disabled, as long as the
    host doesn't change state. At state change, notifications are re-enabled.

    Args:
        connection: A livestatus connection object.
        host_name: Host name for which this acknowledgement is for.
        sticky: If set, only a state-change to the UP/OK state will discard the acknowledgement.
                Otherwise, it will be discarded on any state-change.
        notify: If set, notifications will be sent out to the configured contacts.
        persistent: If set, the comment will persist a restart.
        user: User ID of the user who acknowledged the problem.
        comment: Comment to be stored alongside the acknowledgement.
        expire_on: If set, the acknowledgement will expire at this time.

    Examples:

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.livestatus_utils.testing import mock_site

        >>> cmd = "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;example.com;1;0;0;;"
        >>> with simple_expect() as live:
        ...     _ = live.expect_query("GET hosts\\nColumns: name\\nFilter: name = example.com")
        ...     _ = live.expect_query(cmd, match_type="ellipsis")
        ...     acknowledge_host_problem(live, 'example.com')

        Not authenticated users can't call this function:

            >>> with mock_site(), application_and_request_context():
            ...     acknowledge_host_problem(live, 'example.com')   # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKAuthException: ...
    """
    _user.need_permission("action.acknowledge")

    with detailed_connection(connection) as conn:
        site_id = Query([Hosts.name], Hosts.name.equals(host_name)).value(conn)

    _acknowledge_problem(
        connection,
        site_id,
        host_name,
        sticky=sticky,
        notify=notify,
        persistent=persistent,
        user=user,
        comment=comment,
        expire_on=expire_on,
    )


def acknowledge_hostgroup_problem(
    connection: MultiSiteConnection,
    hostgroup_name: str,
    sticky: bool = False,
    notify: bool = False,
    persistent: bool = False,
    user: UserId = UserId.builtin(),
    comment: str = "",
    expire_on: dt.datetime | None = None,
) -> None:
    """Acknowledge the problems of the current hosts of the host group

    When acknowledging a problem, further notifications for the respective services are disabled, as
    long as a specific service doesn't change state. At state change, notifications are re-enabled.

    Args:
        connection: A livestatus connection object.
        hostgroup_name: Host group name for which this acknowledgement is for.
        sticky: If set, only a state-change to the UP/OK state will discard the acknowledgement.
                Otherwise, it will be discarded on any state-change.
        notify: If set, notifications will be sent out to the configured contacts.
        persistent: If set, the comment will persist a restart.
        user: User ID of the user who acknowledged the problem.
        comment: Comment to be stored alongside the acknowledgement.
        expire_on: If set, the acknowledgement will expire at this time.

    Raises:
        ValueError:
            when the host group in question doesn't exist.
    """
    _user.need_permission("action.acknowledge")

    with detailed_connection(connection) as conn:
        group_entries = Query(
            [tables.Hostgroups.members], tables.Hostgroups.name.equals(hostgroup_name)
        ).fetchall(conn)

    for entry in group_entries:
        site_id = entry["site"]
        for host_name in entry["members"]:
            _acknowledge_problem(
                connection,
                site_id,
                host_name,
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                user=user,
                comment=comment,
                expire_on=expire_on,
            )


def _query_site(connection: MultiSiteConnection, host_name: str) -> SiteId:
    with detailed_connection(connection) as conn:
        site_id = Query([Hosts.name], Hosts.name.equals(host_name)).first_value(conn)
        if not isinstance(site_id, str):
            raise QueryException
    return SiteId(site_id)
