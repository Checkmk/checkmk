#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import Discriminator

import cmk.web.utils.permission_verification as permissions
from cmk.gui import sites, visuals
from cmk.gui.i18n import _l
from cmk.gui.logged_in import user
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
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.type_defs import VisualContext, VisualName
from cmk.livestatus_client import MKLivestatusNotFoundError
from cmk.web.utils.speaklater import LazyString

from ._contextual_link_encoding import EffectiveLink, link_properties_for
from ._family import DASHBOARD_FAMILY
from ._widget_resolution import (
    PERMISSIONS_LINK_TARGET,
    PERMISSIONS_WIDGET_QUERY,
    resolve_widget,
    ResolvedWidget,
)
from .model.contextual_link import VisualLocation
from .model.link_properties import LinkProperties, ResolvedLink
from .model.response_model import ComputedWidgetResponse
from .model.widget_content.stats import EventStatsContent, HostStatsContent, ServiceStatsContent
from .model.widget_source import ExplicitWidgetContent, SavedWidgetContent

type StatsContent = Annotated[
    HostStatsContent | ServiceStatsContent | EventStatsContent, Discriminator("type")
]
type StatsSource = Annotated[
    ExplicitWidgetContent[StatsContent] | SavedWidgetContent, Discriminator("type")
]


@api_model
class StatsRequest:
    source: StatsSource = api_field(description="The widget to compute.")


type HostStatsCategory = Literal["up", "downtime", "unreachable", "down"]
type ServiceStatsCategory = Literal["ok", "downtime", "host_down", "warning", "unknown", "critical"]
type EventStatsCategory = Literal["ok", "warning", "unknown", "critical"]
type StatsCategory = HostStatsCategory | ServiceStatsCategory | EventStatsCategory


@api_model
class StatsPart:
    category: StatsCategory = api_field(description="The states the objects of this part share.")
    count: int = api_field(description="The number of objects in this part.")
    link_properties: LinkProperties = api_field(
        description="What a click on this part carries per link."
    )


@api_model
class StatsTotal:
    count: int = api_field(description="The number of objects in all parts.")
    link_properties: LinkProperties = api_field(
        description="What a click on the total carries per link."
    )


@api_model
class Stats:
    links: list[ResolvedLink] = api_field(description="The resolved links of the widget.")
    parts: list[StatsPart] = api_field(description="The parts, from the outermost ring inwards.")
    total: StatsTotal = api_field(description="The sum over all parts.")


_NOT_IN_HOST_DOWNTIME = {"is_host_scheduled_downtime_depth": "0"}
_NOT_IN_DOWNTIME = {"is_in_downtime": "0"}

_HOST_STATS_QUERY = (
    "GET hosts\n"
    # Up
    "Stats: state = 0\n"
    "Stats: scheduled_downtime_depth = 0\n"
    "StatsAnd: 2\n"
    # Downtime
    "Stats: scheduled_downtime_depth > 0\n"
    # Unreachable
    "Stats: state = 2\n"
    "Stats: scheduled_downtime_depth = 0\n"
    "StatsAnd: 2\n"
    # Down
    "Stats: state = 1\n"
    "Stats: scheduled_downtime_depth = 0\n"
    "StatsAnd: 2\n"
    # Filter
    "Filter: custom_variable_names < _REALNAME"
)

_HOST_PARTS: Sequence[tuple[HostStatsCategory, VisualContext]] = (
    (
        "up",
        {"hoststate": {"hst0": "on"}, "host_scheduled_downtime_depth": _NOT_IN_HOST_DOWNTIME},
    ),
    ("downtime", {"host_scheduled_downtime_depth": {"is_host_scheduled_downtime_depth": "1"}}),
    (
        "unreachable",
        {"hoststate": {"hst2": "on"}, "host_scheduled_downtime_depth": _NOT_IN_HOST_DOWNTIME},
    ),
    (
        "down",
        {"hoststate": {"hst1": "on"}, "host_scheduled_downtime_depth": _NOT_IN_HOST_DOWNTIME},
    ),
)

_SERVICE_STATS_QUERY = (
    "GET services\n"
    # OK
    "Stats: state = 0\n"
    "Stats: scheduled_downtime_depth = 0\n"
    "Stats: host_scheduled_downtime_depth = 0\n"
    "Stats: host_state = 0\n"
    "Stats: host_has_been_checked = 1\n"
    "StatsAnd: 5\n"
    # Downtime
    "Stats: scheduled_downtime_depth > 0\n"
    "Stats: host_scheduled_downtime_depth > 0\n"
    "StatsOr: 2\n"
    # Down host
    "Stats: scheduled_downtime_depth = 0\n"
    "Stats: host_scheduled_downtime_depth = 0\n"
    "Stats: host_state != 0\n"
    "StatsAnd: 3\n"
    # Warning
    "Stats: state = 1\n"
    "Stats: scheduled_downtime_depth = 0\n"
    "Stats: host_scheduled_downtime_depth = 0\n"
    "Stats: host_state = 0\n"
    "Stats: host_has_been_checked = 1\n"
    "StatsAnd: 5\n"
    # Unknown
    "Stats: state = 3\n"
    "Stats: scheduled_downtime_depth = 0\n"
    "Stats: host_scheduled_downtime_depth = 0\n"
    "Stats: host_state = 0\n"
    "Stats: host_has_been_checked = 1\n"
    "StatsAnd: 5\n"
    # Critical
    "Stats: state = 2\n"
    "Stats: scheduled_downtime_depth = 0\n"
    "Stats: host_scheduled_downtime_depth = 0\n"
    "Stats: host_state = 0\n"
    "Stats: host_has_been_checked = 1\n"
    "StatsAnd: 5\n"
    # Filter
    "Filter: host_custom_variable_names < _REALNAME"
)

_SERVICE_PARTS: Sequence[tuple[ServiceStatsCategory, VisualContext]] = (
    (
        "ok",
        {
            "hoststate": {"hst0": "on"},
            "svcstate": {"st0": "on"},
            "in_downtime": _NOT_IN_DOWNTIME,
        },
    ),
    ("downtime", {"in_downtime": {"is_in_downtime": "1"}}),
    (
        "host_down",
        {
            "hoststate": {"hst1": "on", "hst2": "on", "hstp": "on"},
            "in_downtime": _NOT_IN_DOWNTIME,
        },
    ),
    (
        "warning",
        {
            "hoststate": {"hst0": "on"},
            "svcstate": {"st1": "on"},
            "in_downtime": _NOT_IN_DOWNTIME,
        },
    ),
    (
        "unknown",
        {
            "hoststate": {"hst0": "on"},
            "svcstate": {"st3": "on"},
            "in_downtime": _NOT_IN_DOWNTIME,
        },
    ),
    (
        "critical",
        {
            "hoststate": {"hst0": "on"},
            "svcstate": {"st2": "on"},
            "in_downtime": _NOT_IN_DOWNTIME,
        },
    ),
)

_EVENT_STATS_QUERY = (
    "GET eventconsoleevents\n"
    "Stats: event_state = 0\n"  # ok
    "Stats: event_state = 1\n"  # warning
    "Stats: event_state = 3\n"  # unknown
    "Stats: event_state = 2"  # critical
)
_RELATED_EVENTS_ONLY = "\nFilter: event_contact_groups != \nFilter: host_name != \nOr: 2"

_EVENT_PARTS: Sequence[tuple[EventStatsCategory, VisualContext]] = (
    ("ok", {"event_state": {"event_state_0": "on"}}),
    ("warning", {"event_state": {"event_state_1": "on"}}),
    ("unknown", {"event_state": {"event_state_3": "on"}}),
    ("critical", {"event_state": {"event_state_2": "on"}}),
)


def _event_stats_query() -> str:
    if user.may("mkeventd.seeall") or user.may("mkeventd.seeunrelated"):
        return _EVENT_STATS_QUERY
    return _EVENT_STATS_QUERY + _RELATED_EVENTS_ONLY


@dataclass(frozen=True)
class _StatsType:
    query: Callable[[], str]
    parts: Sequence[tuple[StatsCategory, VisualContext]]
    link_title: LazyString
    view_name: VisualName


_STATS_BY_TYPE: Mapping[str, _StatsType] = {
    HostStatsContent.internal_type(): _StatsType(
        query=lambda: _HOST_STATS_QUERY,
        parts=_HOST_PARTS,
        link_title=_l("All hosts"),
        view_name="searchhost",
    ),
    ServiceStatsContent.internal_type(): _StatsType(
        query=lambda: _SERVICE_STATS_QUERY,
        parts=_SERVICE_PARTS,
        link_title=_l("All services"),
        view_name="searchsvc",
    ),
    EventStatsContent.internal_type(): _StatsType(
        query=_event_stats_query,
        parts=_EVENT_PARTS,
        link_title=_l("All events"),
        view_name="ec_events",
    ),
}
STATS_TYPES = frozenset(_STATS_BY_TYPE)


def _built_in_link(content: StatsContent, _context: VisualContext) -> EffectiveLink:
    stats_type = _STATS_BY_TYPE[content.internal_type()]
    return EffectiveLink(
        title=str(stats_type.link_title),
        location=VisualLocation(type="views", name=stats_type.view_name),
        include_context=True,
        include_time_range=False,
        show_filter_form=True,
    )


def _counted_parts(widget: ResolvedWidget) -> list[tuple[StatsCategory, VisualContext, int]]:
    stats_type = _STATS_BY_TYPE[widget.config["type"]]
    filter_headers, only_sites = visuals.get_filter_headers(
        infos=widget.infos, context=widget.context
    )
    try:
        with sites.only_sites(only_sites):
            counts = sites.live().query_summed_stats(stats_type.query() + "\n" + filter_headers)
    except MKLivestatusNotFoundError:
        counts = []
    return [
        (category, native_key, count)
        for (category, native_key), count in zip(
            stats_type.parts, counts or [0] * len(stats_type.parts), strict=True
        )
    ]


def compute_stats(api_context: ApiContext, body: StatsRequest) -> ComputedWidgetResponse[Stats]:
    """Compute a host, service or event statistics widget."""
    with resolve_widget(api_context, body.source, STATS_TYPES, _built_in_link) as widget:
        counted_parts = _counted_parts(widget)
        return ComputedWidgetResponse(
            domainType="widget-compute",
            value=Stats(
                links=[link.to_api() for link in widget.links],
                parts=[
                    StatsPart(
                        category=category,
                        count=count,
                        link_properties=link_properties_for(widget.links, native_key),
                    )
                    for category, native_key, count in counted_parts
                ],
                total=StatsTotal(
                    count=sum(count for _category, _native_key, count in counted_parts),
                    link_properties=link_properties_for(widget.links, {}),
                ),
            ),
        )


ENDPOINT_COMPUTE_STATS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href(domain_type="dashboard", action="compute-stats"),
        link_relation="cmk/compute_stats",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm([PERMISSIONS_WIDGET_QUERY, PERMISSIONS_LINK_TARGET])
    ),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=compute_stats)},
    allowed_tokens={"dashboard"},
)
