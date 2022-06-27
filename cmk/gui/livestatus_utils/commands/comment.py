#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains helpers to set comments for host and service.
"""
from cmk.gui.livestatus_utils.commands.lowlevel import send_command
from cmk.gui.logged_in import user as _user


def add_host_comment(
    connection,
    host_name: str,
    comment: str,
    persistent: bool = False,
    user: str = "",
):
    """Add a comment for a particular host.

    Args:
        connection:
            A livestatus connection object

        host_name:
            The host-name for which the comment is for

        comment:
            The comment which will be stored for the host

        persistent:
            If set, the comment will persist across program restarts until it is deleted manually.
            If not set, the comment will be deleted the next time the Core is restarted.

        user:

    Examples:

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.logged_in import SuperUserContext
        >>> from cmk.gui.config import load_config

        >>> cmd = "COMMAND [...] ADD_HOST_COMMENT;example.com;0;;test"
        >>> expect = simple_expect(cmd, match_type="ellipsis")
        >>> with expect as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     add_host_comment(live, 'example.com', 'test')


    """
    _user.need_permission("action.addcomment")

    return send_command(
        connection,
        "ADD_HOST_COMMENT",
        [host_name, int(persistent), user, comment],
    )


def del_host_comment(connection, comment_id: int):
    """Delete a host comment

    Args:
        connection:
            A livestatus connection object

        comment_id:
            The id of the host comment

    Examples:
        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.logged_in import SuperUserContext
        >>> from cmk.gui.config import load_config

        >>> cmd = "COMMAND [...] DEL_HOST_COMMENT;1234"
        >>> expect = simple_expect(cmd, match_type="ellipsis")
        >>> with expect as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     del_host_comment(live, 1234)

    """
    _user.need_permission("action.addcomment")  # also for removing comments

    return send_command(
        connection,
        "DEL_HOST_COMMENT",
        [comment_id],
    )


def add_service_comment(
    connection,
    host_name: str,
    service_description: str,
    comment: str,
    persistent: bool = False,
    user: str = "",
):
    """Add service comment

    Args:
        connection:
            A livestatus connection object

        host_name:
            The host-name where the service is located

        service_description:
            The service description for which the comment is for

        comment:
            The comment which will be stored for the service

        persistent:
            If set, the comment will persist across program restarts until it is deleted manually.
            If not set, the comment will be deleted the next time the Core is restarted.

        user:

    Examples:
        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.logged_in import SuperUserContext
        >>> from cmk.gui.config import load_config

        >>> cmd = "COMMAND [...] ADD_SVC_COMMENT;example.com;CPU Load;0;;test"
        >>> expect = simple_expect(cmd, match_type="ellipsis")
        >>> with expect as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     add_service_comment(live, 'example.com', 'CPU Load', 'test')


    """
    _user.need_permission("action.addcomment")

    return send_command(
        connection,
        "ADD_SVC_COMMENT",
        [host_name, service_description, int(persistent), user, comment],
    )


def del_service_comment(connection, comment_id: int):
    """Delete a service comment

    Args:
        connection:
            A livestatus connection object

        comment_id:
            The id of the service comment

    Examples:
        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.logged_in import SuperUserContext
        >>> from cmk.gui.config import load_config

        >>> cmd = "COMMAND [...] DEL_SVC_COMMENT;1234"
        >>> expect = simple_expect(cmd, match_type="ellipsis")
        >>> with expect as live, application_and_request_context(), SuperUserContext():
        ...     load_config()
        ...     del_service_comment(live, 1234)

    """
    _user.need_permission("action.addcomment")  # also for removing comments

    return send_command(
        connection,
        "DEL_SVC_COMMENT",
        [comment_id],
    )
