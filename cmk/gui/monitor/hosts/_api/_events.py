#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Annotated, Self

from annotated_types import Interval

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.utils import ProblemException
from cmk.web.utils import permission_verification as permissions

from .._impl import LiveStatusEventRepository, LiveStatusHostRepository
from .._models import Event, UnixTimestamp
from .._repositories import EventRepository, HostRepository
from ._event_icons import EventIcon
from ._family import MONITOR_HOSTS_FAMILY
from ._urls import host_view_link_by_id, service_view_link_by_id

_DEFAULT_TIME_WINDOW_DAYS = 8
_MAX_TIME_WINDOW_DAYS = 365

_DEFAULT_LIMIT = 100
_MAX_LIMIT = 5_000

_SECONDS_PER_DAY = 86400


@api_model
class EventEntry:
    time: UnixTimestamp = api_field(
        description="Unix timestamp the event was logged at", example=1752405510
    )
    event: str = api_field(description="The type of the event", example="SERVICE ALERT")
    service_name: str | None = api_field(
        description=(
            "Name of the service the event belongs to. Null for an event of the host itself."
        ),
        example="CPU utilization",
    )
    state_info: str = api_field(
        description=(
            "State information of the event, e.g. whether a state is hard or soft. Empty for "
            "events that carry none."
        ),
        example="HARD",
    )
    plugin_output: str = api_field(
        description="The check plug-in output logged with the event",
        example="CRIT - load average: 12.10, 9.05, 7.01",
    )
    icon: EventIcon | None = api_field(
        description=(
            "The icon representing this event, resolved server side. Null for an event the "
            "monitoring log holds no icon for."
        ),
        example=None,
    )

    @classmethod
    def from_domain(cls, event: Event) -> Self:
        return cls(
            time=event.time,
            event=event.type,
            service_name=event.service_name,
            state_info=event.state_information,
            plugin_output=event.plugin_output,
            icon=EventIcon.from_event(event),
        )


@api_model
class EventsMeta:
    limit: int = api_field(description="Applied row limit.", example=_DEFAULT_LIMIT)
    truncated: bool = api_field(
        description="Whether the row limit cut off older events.", example=False
    )
    since: UnixTimestamp = api_field(
        description="Unix timestamp the queried time window starts at", example=1751714310
    )
    time_window_days: int = api_field(
        description=(
            "Number of days the returned events actually cover. Equal to the requested time "
            "window, unless the response was truncated - then it is the window ending at the "
            "oldest event still shown, rounded up to a whole day."
        ),
        example=_DEFAULT_TIME_WINDOW_DAYS,
    )
    legacy_events_link: str = api_field(
        description="URL to the legacy view holding the full event history of the same subject",
        example="view.py?view_name=hostsvcevents&site=local&host=web-server-01",
    )


@api_model
class EventsResponse:
    events: list[EventEntry] = api_field(
        description="The events of the queried subject, newest first", example=[]
    )
    meta: EventsMeta = api_field(description="Response metadata")


def get_host_events(
    hostname: Annotated[
        AnnotatedHostName,
        PathParam(description="The host name", example="web-server-01"),
    ],
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)],
        QueryParam(description="An existing site id", example="local"),
    ],
    service_name: Annotated[
        str | None,
        QueryParam(
            description=(
                "Restrict the events to this service of the host. Omit to get the events of the "
                "host itself alongside those of all its services."
            ),
            example="CPU utilization",
        ),
    ] = None,
    time_window_days: Annotated[
        Annotated[int, Interval(ge=1, le=_MAX_TIME_WINDOW_DAYS)],
        QueryParam(
            description="Number of days to look back for events.",
            example=str(_DEFAULT_TIME_WINDOW_DAYS),
        ),
    ] = _DEFAULT_TIME_WINDOW_DAYS,
    limit: Annotated[
        Annotated[int, Interval(ge=1, le=_MAX_LIMIT)],
        QueryParam(description="Maximum number of events to return.", example=str(_DEFAULT_LIMIT)),
    ] = _DEFAULT_LIMIT,
) -> EventsResponse:
    """Show the recent events of a host, or of one of its services."""
    now = int(time.time())
    with sites.only_sites(site_id):
        connection = sites.live()

        return _handle_get_host_events(
            LiveStatusHostRepository(connection=connection),
            LiveStatusEventRepository(connection=connection),
            hostname=hostname,
            site_id=site_id,
            service_name=service_name,
            since=now - time_window_days * _SECONDS_PER_DAY,
            time_window_days=time_window_days,
            limit=limit,
            now=now,
        )


def _handle_get_host_events(
    host_repo: HostRepository,
    event_repo: EventRepository,
    *,
    hostname: str,
    site_id: str,
    service_name: str | None = None,
    since: UnixTimestamp,
    time_window_days: int = _DEFAULT_TIME_WINDOW_DAYS,
    limit: int = _DEFAULT_LIMIT,
    now: UnixTimestamp | None = None,
) -> EventsResponse:
    if not host_repo.host_exists(hostname):
        raise ProblemException(
            status=404,
            title="The requested host was not found",
            detail=f"The host {hostname!r} was not found on site {site_id!r}",
        )

    events = event_repo.fetch(
        hostname=hostname,
        service_name=service_name,
        since=since,
        limit=limit + 1,
    )
    shown_events = events[:limit]
    truncated = len(events) > limit

    return EventsResponse(
        events=[EventEntry.from_domain(event) for event in shown_events],
        meta=EventsMeta(
            limit=limit,
            truncated=truncated,
            since=since,
            time_window_days=(
                _covered_window_days(
                    shown_events[-1].time, now=now if now is not None else int(time.time())
                )
                if truncated and shown_events
                else time_window_days
            ),
            legacy_events_link=(
                host_view_link_by_id("hostsvcevents", site_id=site_id, hostname=hostname)
                if service_name is None
                else service_view_link_by_id(
                    "svcevents", site_id=site_id, hostname=hostname, service_name=service_name
                )
            ),
        ),
    )


def _covered_window_days(oldest_shown: UnixTimestamp, *, now: UnixTimestamp) -> int:
    """Days between `oldest_shown` and `now`, rounded up and floored at one.

    Used only for a truncated response, which covers less than the requested window - down to
    whichever event was the oldest that still fit under the row limit. Rounded up because a
    window reaching into part of an extra day still reaches back into that day, and floored at
    one because that remainder can be under a day and "the last 0 days" reads as broken rather
    than as today.
    """
    return max(1, -(-(now - oldest_shown) // _SECONDS_PER_DAY))


ENDPOINT_GET_HOST_EVENTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/{hostname}/events",
        link_relation="cmk/list_host_events",
        method="get",
    ),
    permissions=EndpointPermissions(
        # Declared for the permission tracker: inspected via user.may() during the request, but
        # none is required.
        required=permissions.Undocumented(
            permissions.AnyPerm(
                [
                    permissions.OkayToIgnorePerm("general.see_all"),
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                ]
            )
        )
    ),
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=get_host_events)},
)
