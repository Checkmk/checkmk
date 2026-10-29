#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId
from cmk.gui import sites
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.web.utils import permission_verification as permissions

from .._commands import HostEventArchiver
from .._impl import LiveStatusHostActions
from .._models import HostTarget
from ._family import MONITOR_HOSTS_FAMILY


@api_model
class ArchiveEventsHostRef:
    site_id: str = api_field(description="Site ID the host belongs to", example="local")
    name: str = api_field(description="Host name", example="web-server-01")


@api_model
class ArchiveEventsRequestBody:
    hosts: list[ArchiveEventsHostRef] = api_field(
        description="The hosts to archive the open Event Console events of.",
    )


@api_model
class ArchiveEventsResponse:
    archived: int = api_field(description="Number of hosts whose events were archived", example=3)


def archive_events(
    api_context: ApiContext, body: ArchiveEventsRequestBody
) -> ArchiveEventsResponse:
    """Archive the open Event Console events of the given hosts."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("mkeventd.archive_events_of_hosts")

    return _handle_archive_events(
        LiveStatusHostActions(connection=sites.live()), body, author=api_context.user.ident
    )


def _handle_archive_events(
    archiver: HostEventArchiver, body: ArchiveEventsRequestBody, *, author: UserId
) -> ArchiveEventsResponse:
    # The selected services of one host name it once.
    targets = list(dict.fromkeys(HostTarget(host.site_id, host.name) for host in body.hosts))
    if targets:
        archiver.archive_events(targets, author=author)
    return ArchiveEventsResponse(archived=len(targets))


ENDPOINT_ARCHIVE_EVENTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/actions/archive_events",
        link_relation="cmk/archive_events",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [
                permissions.Perm("general.act"),
                permissions.Perm("mkeventd.archive_events_of_hosts"),
                # sites.live() authenticates the user, which checks these permissions.
                permissions.Perm("general.see_all"),
                permissions.OkayToIgnorePerm("bi.see_all"),
                permissions.OkayToIgnorePerm("mkeventd.seeall"),
            ]
        )
    ),
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=archive_events)},
)
