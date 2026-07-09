#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""On-demand object detail/picker queries for the Maps SPA.

These are single-object, on-demand reads (drawer details, editor pickers) — they
do NOT feed the SSE state stream and do not scale with the host count, so they
belong in the GUI rather than the daemon (which owns only the live-state plane).

They run through ``cmk.gui.sites.live()``, which is auth-scoped to the logged-in
user's contact groups automatically — so a user only ever sees objects they are
authorised for (unlike the daemon command path this replaces; see the Maps
backend review #4).

The results are plain frozen dataclasses; :mod:`cmk.maps.rest_api.internal` maps
them onto the wire models its endpoints publish.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.sites import live
from cmk.gui.user_sites import get_configured_site_choices
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.livestatus_client import lqencode
from cmk.livestatus_client.expressions import And
from cmk.livestatus_client.queries import Query, ResultRow
from cmk.livestatus_client.tables.hosts import Hosts
from cmk.livestatus_client.tables.services import Services
from cmk.maps.shared.autocomplete import object_autocomplete_query, unique_names
from cmk.maps.shared.filters import normalize_object_filter
from cmk.maps.shared.geo import resolve_host_coords
from cmk.maps.shared.perfdata import parse_perf_metrics
from cmk.maps.shared.states import HOST_STATE_MAP, SERVICE_STATE_MAP

# Autocomplete hard cap — a multi-million-object site filters + bounds at the
# source instead of streaming every name into the editor. The GUI picker caps
# tighter than the daemon's API default; the SPA narrows further as you type.
_AUTOCOMPLETE_LIMIT = 100

_HOST_MEMBER_COLUMNS = [
    Hosts.name,
    Hosts.state,
    Hosts.plugin_output,
    Hosts.acknowledged,
    Hosts.scheduled_downtime_depth,
    Hosts.notifications_enabled,
    Hosts.last_state_change,
]
_SVC_MEMBER_COLUMNS = [
    Services.host_name,
    Services.description,
    Services.state,
    Services.plugin_output,
    Services.acknowledged,
    Services.scheduled_downtime_depth,
    Services.notifications_enabled,
    Services.last_state_change,
]


@dataclass(frozen=True, kw_only=True)
class GeoCoordinates:
    lat: float
    lng: float


@dataclass(frozen=True, kw_only=True)
class PerfMetricsSource:
    """An object's raw perfdata plus the labels parsed out of it."""

    perf_data: str
    check_command: str
    metrics: list[str]


@dataclass(frozen=True, kw_only=True)
class Member:
    """One host or service in a group's / dyngroup's member triage list."""

    host: str
    service: str
    state: str
    output: str
    acknowledged: bool
    in_downtime: bool
    notifications_enabled: bool
    last_state_change: float | None


@dataclass(frozen=True, kw_only=True)
class FolderChoice:
    path: str
    title: str


@dataclass(frozen=True, kw_only=True)
class SiteChoice:
    site_id: str
    alias: str


def _first_line(output: object) -> str:
    return str(output or "").split("\n", 1)[0]


def _int(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _timestamp(value: object) -> float | None:
    """Livestatus emits 0 for "never changed"; the SPA renders that as unknown."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value:
        return float(value)
    return None


# ---------------------------------------------------------------------------
# Host geo coordinates (worldmap placement)
# ---------------------------------------------------------------------------


def host_geo(host: str) -> GeoCoordinates | None:
    """Coordinates for a host, from its Maps labels or legacy custom variables.

    Mirrors the daemon's resolution order: the ``maps_lat``/``maps_lng`` host
    labels first, then the legacy ``LAT``/``LONG`` custom variables.
    """
    row = Query(
        [Hosts.labels, Hosts.custom_variable_names, Hosts.custom_variable_values],
        Hosts.name == host,
    ).first(live())
    if row is None:
        return None

    labels = row["labels"] if isinstance(row["labels"], dict) else {}
    names = row["custom_variable_names"]
    values = row["custom_variable_values"]
    custom_vars = {
        str(name): value
        for name, value in zip(
            names if isinstance(names, list) else [],
            values if isinstance(values, list) else [],
            strict=False,
        )
    }
    coords = resolve_host_coords(labels, custom_vars)
    return None if coords is None else GeoCoordinates(lat=coords[0], lng=coords[1])


# ---------------------------------------------------------------------------
# Perfdata source (drawer metric picker)
# ---------------------------------------------------------------------------


def perf_metrics(host: str, service: str | None) -> PerfMetricsSource:
    """The raw perfdata of one object, plus the metric labels parsed out of it."""
    if service:
        row = Query(
            [Services.perf_data, Services.check_command],
            And(Services.host_name == host, Services.description == service),
        ).first(live())
        perf_data = str(row["perf_data"] or "") if row else ""
        check_command = str(row["check_command"] or "") if row else ""
    else:
        row = Query([Hosts.perf_data], Hosts.name == host).first(live())
        perf_data = str(row["perf_data"] or "") if row else ""
        check_command = ""
    return PerfMetricsSource(
        perf_data=perf_data,
        check_command=check_command,
        metrics=[m["label"] for m in parse_perf_metrics(perf_data)],
    )


# ---------------------------------------------------------------------------
# Object autocomplete (editor)
# ---------------------------------------------------------------------------


def object_names(obj_type: str, host: str | None, search: str | None) -> list[str]:
    """Matching object names for the editor autocomplete (auth-scoped).

    The query text comes from ``cmk.maps.shared.autocomplete``: the same builder
    serves the Flask-free daemon, and ``cmk.maps.shared`` must not depend on the
    livestatus client, so it emits raw LQL. Hence no column-typed ``Query`` on
    this one path — the shared seam owns the query.
    """
    query = object_autocomplete_query(
        obj_type, escape=lqencode, limit=_AUTOCOMPLETE_LIMIT, host=host, search=search
    )
    if query is None:
        return []
    return unique_names(str(row[0]) for row in live().query(query))


# ---------------------------------------------------------------------------
# Group / dyngroup member triage lists (drawer)
# ---------------------------------------------------------------------------


def _host_members(rows: Iterable[ResultRow]) -> list[Member]:
    return [
        Member(
            host=str(row["name"]),
            service="",
            state=HOST_STATE_MAP.get(_int(row["state"]), "UNKNOWN"),
            output=_first_line(row["plugin_output"]),
            acknowledged=bool(row["acknowledged"]),
            in_downtime=_int(row["scheduled_downtime_depth"]) > 0,
            notifications_enabled=bool(row["notifications_enabled"]),
            last_state_change=_timestamp(row["last_state_change"]),
        )
        for row in rows
        if row["name"]
    ]


def _service_members(rows: Iterable[ResultRow]) -> list[Member]:
    return [
        Member(
            host=str(row["host_name"]),
            service=str(row["description"]),
            state=SERVICE_STATE_MAP.get(_int(row["state"]), "UNKNOWN"),
            output=_first_line(row["plugin_output"]),
            acknowledged=bool(row["acknowledged"]),
            in_downtime=_int(row["scheduled_downtime_depth"]) > 0,
            notifications_enabled=bool(row["notifications_enabled"]),
            last_state_change=_timestamp(row["last_state_change"]),
        )
        for row in rows
        if row["host_name"] and row["description"]
    ]


def group_members(group_type: str, group_name: str) -> list[Member]:
    """Per-member state for a host- or service-group (drawer Members tab)."""
    if group_type == "hostgroup":
        # ``==`` on a list column is a membership filter (``groups >= <name>``).
        return _host_members(
            Query(_HOST_MEMBER_COLUMNS, Hosts.groups == group_name).fetchall(live())
        )
    if group_type == "servicegroup":
        return _service_members(
            Query(_SVC_MEMBER_COLUMNS, Services.groups == group_name).fetchall(live())
        )
    return []


def _checked_object_filter(value: str) -> str:
    # A dyngroup filter is spliced straight into an LQL query; the shared
    # allowlist (cmk.maps.shared.filters) rejects anything but safe combinator
    # headers so an escaped newline can't smuggle in Stats:/Columns:/GET.
    try:
        return normalize_object_filter(value)
    except ValueError:
        raise MKUserError(
            "object_filter", _("object_filter must be one or more 'Filter: …' lines.")
        )


def dyngroup_members(object_types: str, object_filter: str) -> list[Member]:
    """Per-member state for a dyngroup filter (drawer Members tab).

    The filter is stored — and evaluated by the daemon — as ready-made
    ``Filter:`` lines, so it rides along as an extra header instead of being
    rebuilt as a typed expression. The allowlist above is what makes that safe.
    """
    headers = [_checked_object_filter(object_filter)]
    if object_types == "service":
        return _service_members(Query(_SVC_MEMBER_COLUMNS, extra_headers=headers).fetchall(live()))
    return _host_members(Query(_HOST_MEMBER_COLUMNS, extra_headers=headers).fetchall(live()))


# ---------------------------------------------------------------------------
# Foldertree editor pickers (GUI-native, no Livestatus)
# ---------------------------------------------------------------------------


def folder_choices() -> list[FolderChoice]:
    """Setup folders for the foldertree root-folder picker.

    Uses the WATO folder tree, which is already scoped to the folders the acting
    user may see — so unlike the daemon endpoint this needs no extra gate.
    """
    return [
        FolderChoice(path=str(path), title=str(title))
        for path, title in folder_tree().folder_choices(user)
    ]


def site_choices() -> list[SiteChoice]:
    """Monitoring sites for the foldertree site-scope picker (auth-scoped)."""
    return [
        SiteChoice(site_id=str(site_id), alias=str(alias))
        for site_id, alias in get_configured_site_choices()
    ]
