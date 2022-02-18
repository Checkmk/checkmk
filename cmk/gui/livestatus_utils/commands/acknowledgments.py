#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains helpers to trigger acknowledgments.
"""
from livestatus import SiteId

from cmk.utils.livestatus_helpers import tables
from cmk.utils.livestatus_helpers.queries import detailed_connection, Query
from cmk.utils.livestatus_helpers.tables import Hosts

from cmk.gui.livestatus_utils.commands.downtimes import QueryException
from cmk.gui.livestatus_utils.commands.lowlevel import send_command
from cmk.gui.logged_in import user as _user


def acknowledge_service_problem(
    connection,
    host_name: str,
    service_description: str,
    sticky: bool = False,
    notify: bool = False,
    persistent: bool = False,
    user: str = "",
    comment: str = "",
):
    """Acknowledge the current problem for the given service.

    When acknowledging a problem, furhter notifications for the service are disabled, as
    long as the service doesn't change state. At state change, notifications are re-enabled.

    Args:
        connection:
            A livestatus connection object.

        host_name:
            The host-name for which this acknowledgement is for.

        service_description:
            The service description of the service, whose problems shall be acknowledged.

        sticky:
            If set, only a state-change of the service to an OK state will discard the
            acknowledgement. Otherwise, it will be discarded on any state-change. Defaults to False.

        notify:
            If set, notifications will be sent out to the configured contacts. Defaults to False.

        persistent:
            If set, the comment will persist a restart. Defaults to False.

        user:
        comment:
            If set, this comment will be stored alongside the acknowledgement.

    Examples:

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.logged_in import SuperUserContext
        >>> from cmk.gui.config import load_config

        >>> cmd = "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;drain;1;0;0;;"
        >>> with simple_expect() as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     _ = live.expect_query("GET hosts\\nColumns: name\\nFilter: name = example.com")
        ...     _ = live.expect_query(cmd, match_type="ellipsis")
        ...     acknowledge_service_problem(live, 'example.com', 'drain')

        Not authenticated users can't call this function:

            >>> with application_and_request_context():
            ...     acknowledge_service_problem(live, 'example.com', 'drain')   # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKAuthException: ...
    """
    _user.need_permission("action.acknowledge")

    site_id = _query_site(connection, host_name)

    acknowledgement = 2 if sticky else 1  # 1: normal, 2: sticky

    return send_command(
        connection,
        "ACKNOWLEDGE_SVC_PROBLEM",
        [
            host_name,
            service_description,
            acknowledgement,
            int(notify),
            int(persistent),
            user,
            comment,
        ],
        site_id=site_id,
    )


def acknowledge_servicegroup_problem(
    connection,
    servicegroup_name: str,
    sticky: bool = False,
    notify: bool = False,
    persistent: bool = False,
    user: str = "",
    comment: str = "",
):
    """Acknowledge the problems of the current services of the service group

    When acknowledging a problem, further notifications for the respective services are disabled, as
    long as a specific service doesn't change state. At state change, notifications are re-enabled.

    Args:
        connection:
            A livestatus connection object.

        servicegroup_name:
            The host-name for which this acknowledgement is for.

        sticky:
            If set, only a state-change of the service to an OK state will discard the
            acknowledgement. Otherwise it will be discarded on any state-change. Defaults to False.

        notify:
            If set, notifications will be sent out to the configured contacts. Defaults to False.

        persistent:
            If set, the comment will persist a restart. Defaults to False.

        user:
        comment:
            If set, this comment will be stored alongside the acknowledgement.

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

    acknowledgement = 2 if sticky else 1  # 1: normal, 2: sticky

    for entry in group_entries:
        site_id = entry["site"]
        for host_name, service_description in entry["members"]:

            send_command(
                connection,
                "ACKNOWLEDGE_SVC_PROBLEM",
                [
                    host_name,
                    service_description,
                    acknowledgement,
                    int(notify),
                    int(persistent),
                    user,
                    comment,
                ],
                site_id=site_id,
            )


def acknowledge_host_problem(
    connection,
    host_name,
    sticky: bool = False,
    notify: bool = False,
    persistent: bool = False,
    user: str = "",
    comment: str = "",
):
    """Acknowledge the current problem for the given host.

    When acknowledging a problem, notifications for the host are disabled, as long as the
    host doesn't change state. At state change, notifications are re-enabled.

    Args:
        connection:
            A livestatus connection object.

        host_name:
            The host-name for which this acknowledgement is for.

        sticky:
            If set, only a state-change of the host to an UP state will discard the acknowledgement.
            Otherwise it will be discarded on any state-change. Defaults to False.

        notify:
            If set, notifications will be sent out to the configured contacts. Defaults to False.

        persistent:
            If set, the comment will persist a restart. Defaults to False.

        user:
        comment:
            If set, this comment will be stored alongside the acknowledgement.

    Examples:

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.logged_in import SuperUserContext
        >>> from cmk.gui.config import load_config

        >>> cmd = "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;example.com;1;0;0;;"
        >>> with simple_expect() as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     _ = live.expect_query("GET hosts\\nColumns: name\\nFilter: name = example.com")
        ...     _ = live.expect_query(cmd, match_type="ellipsis")
        ...     acknowledge_host_problem(live, 'example.com')

        Not authenticated users can't call this function:

            >>> with application_and_request_context():
            ...     acknowledge_host_problem(live, 'example.com')   # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKAuthException: ...

    """
    _user.need_permission("action.acknowledge")

    acknowledgement = 2 if sticky else 1  # 1: normal, 2: sticky

    with detailed_connection(connection) as conn:
        site_id = Query([Hosts.name], Hosts.name.equals(host_name)).first_value(conn)

    return send_command(
        connection,
        "ACKNOWLEDGE_HOST_PROBLEM",
        [
            host_name,
            acknowledgement,
            int(notify),
            int(persistent),
            user,
            comment,
        ],
        site_id=site_id,
    )


def acknowledge_hostgroup_problem(
    connection,
    hostgroup_name: str,
    sticky: bool = False,
    notify: bool = False,
    persistent: bool = False,
    user: str = "",
    comment: str = "",
):
    """Acknowledge the problems of the current hosts of the host group

    When acknowledging a problem, further notifications for the respective services are disabled, as
    long as a specific service doesn't change state. At state change, notifications are re-enabled.

    Args:
        connection:
            A livestatus connection object.

        hostgroup_name:
            The name of the host group.

        sticky:
            If set, only a state-change of the service to an OK state will discard the
            acknowledgement. Otherwise it will be discarded on any state-change. Defaults to False.

        notify:
            If set, notifications will be sent out to the configured contacts. Defaults to False.

        persistent:
            If set, the comment will persist a restart. Defaults to False.

        user:
        comment:
            If set, this comment will be stored alongside the acknowledgement.

    Raises:
        ValueError:
            when the host group in question doesn't exist.

    """
    _user.need_permission("action.acknowledge")

    with detailed_connection(connection) as conn:
        group_entries = Query(
            [tables.Hostgroups.members], tables.Hostgroups.name.equals(hostgroup_name)
        ).fetchall(conn)

    acknowledgement = 2 if sticky else 1  # 1: normal, 2: sticky

    for entry in group_entries:
        site_id = entry["site"]
        for host_name in entry["members"]:
            send_command(
                connection,
                "ACKNOWLEDGE_HOST_PROBLEM",
                [
                    host_name,
                    acknowledgement,
                    int(notify),
                    int(persistent),
                    user,
                    comment,
                ],
                site_id=site_id,
            )


def _query_site(connection, host_name: str) -> SiteId:
    with detailed_connection(connection) as conn:
        site_id = Query([Hosts.name], Hosts.name.equals(host_name)).first_value(conn)
        if not isinstance(site_id, str):
            raise QueryException
    return SiteId(site_id)
