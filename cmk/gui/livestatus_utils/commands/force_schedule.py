#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains helpers to set comments for host and service."""

import datetime as dt

from livestatus import MultiSiteConnection

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site
from cmk.gui.logged_in import user as _user
from cmk.livestatus_client.commands import (
    ScheduleForcedHostCheck,
    ScheduleForcedServiceCheck,
)


def force_schedule_host_check(
    connection: MultiSiteConnection, host_name: HostName, check_time: dt.datetime
) -> None:
    """Schedule a forced active check of a particular host

    Args:
        connection:
            A livestatus connection object

        host_name:
            The name of the host where the forced check should be performed on

        check_time:
            The time at which this forced check should be performed


    """
    _user.need_permission("action.reschedule")
    connection.command_obj(
        ScheduleForcedHostCheck(host_name=host_name, check_time=check_time), omd_site()
    )


def force_schedule_service_check(
    connection: MultiSiteConnection,
    host_name: HostName,
    service_description: str,
    check_time: dt.datetime,
) -> None:
    """Schedule a forced active check of a particular service

    Args:
        connection:
            A livestatus connection object

        host_name:
            The name of the host where the service is

        service_description:
            The service name for which the forced check should be performed on

        check_time:
            The time at which this forced check should be performed

    """
    _user.need_permission("action.reschedule")
    connection.command_obj(
        ScheduleForcedServiceCheck(
            host_name=host_name,
            description=service_description,
            check_time=check_time,
        ),
        omd_site(),
    )
