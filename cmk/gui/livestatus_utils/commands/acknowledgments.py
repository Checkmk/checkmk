#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains helpers to trigger acknowledgments."""

import datetime as dt

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.logged_in import user as _user
from cmk.livestatus_client import (
    AcknowledgeHostProblem,
    Acknowledgement,
    AcknowledgeServiceProblem,
    Command,
    LivestatusClient,
    MultiSiteConnection,
    RemoveHostAcknowledgement,
    RemoveServiceAcknowledgement,
    tables,
)
from cmk.livestatus_client.queries import detailed_connection, Query


def _acknowledge_problem(
    connection: MultiSiteConnection,
    site_id: SiteId,
    host_name: HostName,
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

    acknowledgement = Acknowledgement.STICKY if sticky else Acknowledgement.NORMAL
    command: Command
    if service_description:
        command = AcknowledgeServiceProblem(
            host_name=host_name,
            acknowledgement=acknowledgement,
            notify=notify,
            persistent=persistent,
            user=user,
            comment=comment,
            description=service_description,
            expire_on=expire_on,
        )
    else:
        command = AcknowledgeHostProblem(
            host_name=host_name,
            acknowledgement=acknowledgement,
            notify=notify,
            persistent=persistent,
            user=user,
            comment=comment,
            expire_on=expire_on,
        )

    LivestatusClient(connection).command(
        command,
        site_id,
    )


def remove_acknowledgement(
    connection: MultiSiteConnection,
    site_id: SiteId,
    host_name: HostName,
    service_description: str | None = None,
) -> None:
    """Remove an acknowledgement for a host or service problem.

    Args:
        connection: A livestatus connection object.
        site_id: Site ID of the host or service.
        host_name: Host name for which this acknowledgement is for.
        service_description: Service name, if acknowledging a service problem.
    """
    command: Command
    if service_description:
        command = RemoveServiceAcknowledgement(
            host_name=host_name,
            description=service_description,
        )
    else:
        command = RemoveHostAcknowledgement(host_name=host_name)

    LivestatusClient(connection).command(
        command,
        site_id,
    )


def acknowledge_service_problem(
    connection: MultiSiteConnection,
    site_id: SiteId,
    host_name: HostName,
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
        site_id: Site ID of the service.
        host_name: Host name for which this acknowledgement is for.
        service_description: Service name for which this acknowledgement is for.
        sticky: If set, only a state-change to the UP/OK state will discard the acknowledgement.
                Otherwise, it will be discarded on any state-change.
        notify: If set, notifications will be sent out to the configured contacts.
        persistent: If set, the comment will persist a restart.
        user: User ID of the user who acknowledged the problem.
        comment: Comment to be stored alongside the acknowledgement.
        expire_on: If set, the acknowledgement will expire at this time.
    """
    _user.need_permission("action.acknowledge")

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
    site_id: SiteId,
    host_name: HostName,
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
        site_id: Site ID of the host.
        host_name: Host name for which this acknowledgement is for.
        sticky: If set, only a state-change to the UP/OK state will discard the acknowledgement.
                Otherwise, it will be discarded on any state-change.
        notify: If set, notifications will be sent out to the configured contacts.
        persistent: If set, the comment will persist a restart.
        user: User ID of the user who acknowledged the problem.
        comment: Comment to be stored alongside the acknowledgement.
        expire_on: If set, the acknowledgement will expire at this time.
    """
    _user.need_permission("action.acknowledge")

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
