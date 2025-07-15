#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains helpers to set comments for host and service."""

import time
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from livestatus import Command, MultiSiteConnection

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

from cmk.utils.livestatus_helpers.expressions import QueryExpression
from cmk.utils.livestatus_helpers.queries import detailed_connection, Query
from cmk.utils.livestatus_helpers.tables.comments import Comments
from cmk.utils.livestatus_helpers.tables.hosts import Hosts
from cmk.utils.livestatus_helpers.tables.services import Services

from cmk.gui.livestatus_utils.commands.lowlevel import send_command

SHORT_COLUMNS = [Comments.id, Comments.is_service]


class CommentQueryException(Exception):
    pass


class CommentParamException(Exception):
    pass


class CollectionName(Enum):
    service = "service"
    all = "all"
    host = "host"


@dataclass
class Comment:
    host_name: str
    id: int
    author: str
    comment: str
    persistent: bool
    entry_time: str
    service_description: str
    is_service: bool
    site: str

    def __post_init__(self):
        self.persistent = bool(self.persistent)
        self.entry_time = time.strftime("%b %d %Y %H:%M:%S", time.gmtime(float(self.entry_time)))

    def __iter__(self):
        for k, v in self.__dict__.items():
            if k == "service_description":
                if self.is_service:
                    yield (k, v)
            else:
                yield (k, v)


def comments_query() -> Query:
    return Query(
        [
            Comments.host_name,
            Comments.id,
            Comments.author,
            Comments.comment,
            Comments.persistent,
            Comments.service_description,
            Comments.entry_time,
            Comments.is_service,
        ]
    )


def get_comments(
    connection: MultiSiteConnection,
    host_name: str | None,
    service_description: str | None,
    query: QueryExpression | None,
    collection_name: CollectionName = CollectionName.all,
) -> Mapping[int, Comment]:
    # When the user tries to filter for service_descriptions on host only comments.
    if collection_name is CollectionName.host and service_description:
        raise CommentParamException

    q = comments_query().filter(query) if query else comments_query()

    match collection_name:
        case CollectionName.host:
            q = q.filter(Comments.is_service.equals(0))

        case CollectionName.service:
            q = q.filter(Comments.is_service.equals(1))

    if host_name:
        q = q.filter(Comments.host_name == host_name)

    if service_description:
        q = q.filter(Comments.service_description == service_description)

    connection.prepend_site = True

    results = {com["id"]: Comment(**com) for com in q.iterate(connection)}

    return results


@dataclass(frozen=True)
class AddHostComment(Command):
    host_name: HostName
    comment: str
    user: UserId = UserId.builtin()
    persistent: bool = False

    @property
    def name(self) -> str:
        return "ADD_HOST_COMMENT"

    @property
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.persistent, self.user, self.comment]


def add_host_comment_by_query(
    connection: MultiSiteConnection,
    query: QueryExpression,
    comment: str,
    user: UserId = UserId.builtin(),
    persistent: bool = False,
) -> None:
    q = Query([Hosts.name]).filter(query)

    with detailed_connection(connection) as conn:
        hosts: list[tuple[SiteId, HostName]] = [
            (row["site"], row["name"]) for row in q.iterate(conn)
        ]

    if not hosts:
        raise CommentQueryException

    for site, host in hosts:
        connection.command_obj(
            AddHostComment(host_name=host, comment=comment, persistent=persistent, user=user),
            site,
        )


def add_service_comment_by_query(
    connection: MultiSiteConnection,
    query: QueryExpression,
    comment_txt: str,
    persistent: bool = False,
    user: UserId = UserId.builtin(),
) -> None:
    q = Query([Services.description, Services.host_name], query)

    with detailed_connection(connection) as conn:
        results = [(row["site"], row["description"], row["host_name"]) for row in q.iterate(conn)]

    if not results:
        raise CommentQueryException

    for site, service_desc, hostname in results:
        add_service_comment(connection, hostname, service_desc, comment_txt, site, persistent, user)


def add_service_comment(
    connection: MultiSiteConnection,
    host_name: str,
    service_description: str,
    comment_txt: str,
    site_id: SiteId,
    persistent: bool = False,
    user: UserId = UserId.builtin(),
) -> None:
    """Add service comment

    Args:
        connection:
            A livestatus connection object

        host_name:
            The host-name where the service is located

        service_description:
            The service name for which the comment is for

        site_id:
            The site name

        comment:
            The comment which will be stored for the service

        persistent:
            If set, the comment will persist across program restarts until it is deleted manually.
            If not set, the comment will be deleted the next time the Core is restarted.

        user:

    Examples:

        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.session import SuperUserContext
        >>> cmd = "COMMAND [...] ADD_SVC_COMMENT;example.com;CPU Load;0;;test"
        >>> with simple_expect() as live, SuperUserContext():
        ...     _ = live.expect_query(cmd, match_type="ellipsis")
        ...     add_service_comment(live, 'example.com', 'CPU Load', 'test', "NO_SITE")


    """

    send_command(
        connection,
        "ADD_SVC_COMMENT",
        [host_name, service_description, int(persistent), user, comment_txt],
        site_id,
    )


def delete_comments(
    connection: MultiSiteConnection,
    query: QueryExpression,
    site_id: SiteId | None,
) -> None:
    """Delete a comment"""

    only_sites = None if site_id is None else [site_id]
    comments = Query(SHORT_COLUMNS, query).fetchall(connection, True, only_sites)

    for comment in comments:
        if comment["is_service"]:
            delete_service_comment(connection, comment["id"], comment["site"])
        else:
            delete_host_comment(connection, comment["id"], comment["site"])


def delete_host_comment(
    connection: MultiSiteConnection, comment_id: int, site_id: SiteId | None
) -> None:
    """Delete a host comment

    Args:
        connection:
            A livestatus connection object

        comment_id:
            The id of the host comment

        site_id:
            The site name

    Examples:
        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.session import SuperUserContext

        >>> cmd = "COMMAND [...] DEL_HOST_COMMENT;1234"
        >>> expect = simple_expect(cmd, match_type="ellipsis")
        >>> with expect as live, SuperUserContext():
        ...     delete_host_comment(live, 1234, "NO_SITE")

    """

    send_command(connection, "DEL_HOST_COMMENT", [comment_id], site_id)


def delete_service_comment(
    connection: MultiSiteConnection, comment_id: int, site_id: SiteId | None
) -> None:
    """Delete a service comment

    Args:
        connection:
            A livestatus connection object

        comment_id:
            The id of the service comment

        site_id:
            The site name

    Examples:
        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.session import SuperUserContext

        >>> cmd = "COMMAND [...] DEL_SVC_COMMENT;1234"
        >>> expect = simple_expect(cmd, match_type="ellipsis")
        >>> with expect as live, SuperUserContext():
        ...     delete_service_comment(live, 1234, "NO_SITE")

    """

    return send_command(connection, "DEL_SVC_COMMENT", [comment_id], site_id)
