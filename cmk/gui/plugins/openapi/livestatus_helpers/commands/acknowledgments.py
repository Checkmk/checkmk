#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains helpers to trigger acknowledgments.
"""
from typing import List

from cmk.gui.plugins.openapi.livestatus_helpers import tables
from cmk.gui.plugins.openapi.livestatus_helpers.commands.lowlevel import send_command

from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query


def acknowledge_service_problem(
    connection,
    host_name: str,
    service_description: str,
    sticky: bool = False,
    notify: bool = False,
    persistent: bool = False,
    user: str = '',
    comment: str = '',
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
            acknowledgement. Otherwise it will be discarded on any state-change. Defaults to False.

        notify:
            If set, notifications will be sent out to the configured contacts. Defaults to False.

        persistent:
            If set, the comment will persist a restart. Defaults to False.

        user:
        comment:
            If set, this comment will be stored alongside the acknowledgement.

    Examples:

        >>> from cmk.gui.plugins.openapi.livestatus_helpers.testing import simple_expect
        >>> cmd = "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;drain;1;0;0;;"
        >>> with simple_expect(cmd, match_type="ellipsis") as live:
        ...     acknowledge_service_problem(live, 'example.com', 'drain')

    """
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
    """Acknowledge the problems of the current services of the servicegroup

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

    """
    members: List[List[str]] = Query(
        [tables.Servicegroups.members],
        tables.Servicegroups.name.equals(servicegroup_name),
    ).value(connection)

    acknowledgement = 2 if sticky else 1  # 1: normal, 2: sticky

    for host_name, service_description in members:
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

        >>> from cmk.gui.plugins.openapi.livestatus_helpers.testing import simple_expect
        >>> cmd = "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;example.com;1;0;0;;"
        >>> with simple_expect(cmd, match_type="ellipsis") as live:
        ...     acknowledge_host_problem(live, 'example.com')

    """
    acknowledgement = 2 if sticky else 1  # 1: normal, 2: sticky

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
    """Acknowledge the problems of the current hosts of the hostgroup

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

    """
    members: List[str] = Query([tables.Hostgroups.members],
                               tables.Hostgroups.name.equals(hostgroup_name)).value(connection)

    acknowledgement = 2 if sticky else 1  # 1: normal, 2: sticky

    for host_name in members:
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
        )
