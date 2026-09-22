#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Response models for the Maps SPA's internal lookup endpoints.

These are the wire contract between the GUI process and the SPA. The frontend
TypeScript types are generated from the internal OpenAPI spec, so a shape change
here surfaces as a type error in the SPA rather than at runtime.
"""

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.maps.gui._settings import MapListView, RenderMode
from cmk.maps.shared.map_payload import LineStyle
from cmk.maps.shared.ticket import CommandVerb

# Mirrors the ``UnitFormat`` enums in cmk-shared-typing, so the generated
# TypeScript lines up with the SPA's own unit-format types instead of widening
# them to plain strings.
NotationType = Literal[
    "decimal", "si", "iec", "standard_scientific", "engineering_scientific", "time"
]
PrecisionType = Literal["auto", "strict"]


@api_model
class MapsGeoCoordinates:
    lat: float = api_field(description="Latitude in decimal degrees.", example=51.05)
    lng: float = api_field(description="Longitude in decimal degrees.", example=13.74)


@api_model
class MapsHostGeoResponse:
    geo: MapsGeoCoordinates | None = api_field(
        description=(
            "The host's coordinates, resolved from its ``maps_lat``/``maps_lng`` "
            "labels or the legacy ``LAT``/``LONG`` custom variables. Null when the "
            "host carries neither."
        ),
    )


@api_model
class MapsPerfMetricsResponse:
    perf_data: str = api_field(
        description="The object's raw perfdata string.",
        example="rta=0.5ms;200;500;0; pl=0%;80;100;;",
    )
    check_command: str = api_field(
        description="The check command that produced the perfdata (empty for hosts).",
        example="check_mk_active-icmp",
    )
    metrics: list[str] = api_field(
        description="The raw perfdata labels, in perfdata order.",
        example=["rta", "pl"],
    )


@api_model
class MapsObjectsResponse:
    objects: list[str] = api_field(
        description=(
            "Matching object names, capped server-side. Service results are "
            "``<host>;<service>`` pairs; every other object type is a plain name."
        ),
        example=["heute", "localhost"],
    )


@api_model
class MapsMember:
    host: str = api_field(description="The member's host name.", example="heute")
    service: str = api_field(
        description="The member's service description (empty for host members).",
        example="CPU load",
    )
    state: str = api_field(description="The member's state name.", example="OK")
    output: str = api_field(
        description="First line of the member's plug-in output.",
        example="15 min load: 0.42",
    )
    acknowledged: bool = api_field(description="Whether the member's problem is acknowledged.")
    in_downtime: bool = api_field(description="Whether the member is in a scheduled downtime.")
    notifications_enabled: bool = api_field(
        description="Whether notifications are enabled for the member."
    )
    last_state_change: float | None = api_field(
        description="Unix timestamp of the last state change, null when unknown.",
        example=1735689600.0,
    )


@api_model
class MapsMembersResponse:
    members: list[MapsMember] = api_field(
        description="Per-member state, auth-scoped to the caller's contact groups.",
        example=[],
    )


@api_model
class MapsFolder:
    path: str = api_field(description="The folder's path.", example="net/dc1")
    title: str = api_field(description="The folder's display title.", example="Data center 1")


@api_model
class MapsFoldersResponse:
    folders: list[MapsFolder] = api_field(
        description="Setup folders the caller may see.", example=[]
    )


@api_model
class MapsSite:
    site_id: str = api_field(
        description="The monitoring site's id.", example="heute", serialization_alias="id"
    )
    alias: str = api_field(description="The site's display alias.", example="Local site")


@api_model
class MapsSitesResponse:
    sites: list[MapsSite] = api_field(
        description="Monitoring sites the caller may see.", example=[]
    )


@api_model
class MapsPerfometerSegment:
    pct: float = api_field(
        description="The segment's share of the gauge, in percent.", example=42.0
    )
    color: str = api_field(description="The segment's fill color.", example="#3d5b9b")


@api_model
class MapsPerfometerSide:
    title: str | None = api_field(
        description="Title of the side's leading plain-metric segment.", example="RAM usage"
    )
    label: str = api_field(description="The side's formatted value label.", example="4.2 GiB")
    pct: float = api_field(
        description="The side's utilization, projected over its own focus range.", example=42.0
    )


@api_model
class MapsPerfometer:
    label: str = api_field(description="The value label the monitoring views show.", example="42%")
    rows: list[list[MapsPerfometerSegment]] = api_field(
        description="The projected segment stacks, including the theme background filler.",
        example=[],
    )
    sides: list[MapsPerfometerSide | None] = api_field(
        description=(
            "Per gauge side (one for a plain Perf-O-Meter, upper/lower for a "
            "stacked one, left/right for a bidirectional one). Null where the "
            "side has no renderable stack."
        ),
        example=[],
    )
    bg_color: str = api_field(
        description="The theme's background filler color, so the SPA can restyle it.",
        example="#333333",
    )


@api_model
class MapsMetricUnitPrecision:
    type: PrecisionType = api_field(description="The precision mode.", example="auto")
    digits: int = api_field(description="Number of digits.", example=2)


@api_model
class MapsMetricUnit:
    notation: NotationType = api_field(description="The unit's notation type.", example="decimal")
    symbol: str = api_field(description="The unit symbol.", example="s")
    precision: MapsMetricUnitPrecision = api_field(description="How to round the formatted value.")


@api_model
class MapsMetric:
    name: str = api_field(description="The metric's canonical registry name.", example="load15")
    title: str = api_field(description="The metric's display title.", example="15 min load")
    scale: float = api_field(
        description="Factor converting the raw perfdata value into the registry's unit.",
        example=1.0,
    )
    unit: MapsMetricUnit = api_field(description="How to format the value.")
    color: str = api_field(
        description="The metric registry's series color, as Checkmk's own graphs draw it.",
        example="#80c0ff",
    )


@api_model
class MapsGraphGroup:
    graph_id: str = api_field(
        description="The graph plug-in's id.", example="cpu_load", serialization_alias="id"
    )
    title: str = api_field(description="The graph's display title.", example="CPU load")
    metrics: list[str] = api_field(
        description="Raw perfdata labels the graph draws.", example=["load1", "load15"]
    )
    mirrored: list[str] = api_field(
        description="Raw perfdata labels drawn below the axis (bidirectional graphs).",
        example=[],
    )


@api_model
class MapsMetricInfoResponse:
    perfometer: MapsPerfometer | None = api_field(
        description="The rendered Perf-O-Meter, or null when no renderer matches."
    )
    metrics: dict[str, MapsMetric] = api_field(
        description=(
            "Display semantics keyed by RAW perfdata label. Labels without a "
            "registry entry are omitted — the SPA falls back to its own heuristics."
        ),
        example={},
    )
    graphs: list[MapsGraphGroup] | ApiOmitted = api_field(
        description=(
            "The graph plug-ins applicable to these metrics. Only present when the "
            "request asked for them (walking every plug-in is too costly for the "
            "per-tick Perf-O-Meter lookups)."
        ),
        default_factory=ApiOmitted,
    )


@api_model
class MapsAggregation:
    aggregation_id: str = api_field(
        description="The resolved aggregation (branch) name.",
        example="Host heute",
        serialization_alias="id",
    )
    title: str = api_field(description="The aggregation's display title.", example="Host heute")
    pack_id: str = api_field(
        description="The BI pack the aggregation belongs to.", example="default"
    )
    function: str = api_field(description="The aggregation function's kind.", example="worst")


@api_model
class MapsAggregationsResponse:
    aggregations: list[MapsAggregation] = api_field(
        description="Resolved BI aggregations the caller may see, sorted by title.",
        example=[],
    )


@api_model
class MapsAggregationNode:
    name: str = api_field(description="The node's display name.", example="Host heute")
    node_type: Literal["bi_aggregator", "bi_leaf"] = api_field(
        description="Whether the node is a rule (aggregator) or a monitored leaf.",
        example="bi_aggregator",
    )
    state: int = api_field(description="The node's computed state.", example=0)
    in_downtime: bool = api_field(description="Whether the node is in a scheduled downtime.")
    acknowledged: bool = api_field(description="Whether the node's problem is acknowledged.")
    output: str = api_field(description="The node's output text.", example="")
    children: list[MapsAggregationNode] = api_field(
        description="Nested nodes; empty at the requested depth limit.", example=[]
    )
    host_name: str | None = api_field(
        description="The leaf's host name (null on aggregator nodes).",
        example="heute",
    )
    service_description: str | None = api_field(
        description="The leaf's service description (null on host leaves and aggregators).",
        example="CPU load",
    )


@api_model
class MapsAggregationTreeResponse:
    tree: MapsAggregationNode | None = api_field(
        description=(
            "The aggregation hierarchy, or null when no matching branch exists, the "
            "caller's scope hides it, or livestatus is unreachable."
        )
    )
    connection_ok: bool = api_field(
        description=(
            "False when livestatus was unreachable — the editor shows the "
            '"unavailable" hint instead of "no such aggregation".'
        )
    )


@api_model
class MapsAggregationState:
    state: int = api_field(description="The aggregation's computed state.", example=0)
    output: str = api_field(description="The aggregation's output text.", example="")
    acknowledged: bool = api_field(description="Whether the problem is acknowledged.")
    in_downtime: bool = api_field(description="Whether the aggregation is in a downtime.")


@api_model
class MapsAggregationStatesResponse:
    states: dict[str, MapsAggregationState] = api_field(
        description="Current state keyed by resolved aggregation name.", example={}
    )


@api_model
class MapsImage:
    name: str = api_field(description="The image's file name.", example="server.svg")
    url: str = api_field(
        description="The image's site-relative URL (served statically by Apache).",
        example="images/server.svg",
    )
    builtin: bool = api_field(
        description="Whether the image ships with Checkmk (cannot be overwritten or deleted)."
    )


@api_model
class MapsImagesResponse:
    images: list[MapsImage] = api_field(
        description="The site's image library: built-in icons plus user uploads.",
        example=[],
    )


@api_model
class MapsImageUsage:
    map_name: str = api_field(
        description="Name of the map referencing the image.",
        example="datacenter",
        serialization_alias="map",
    )
    alias: str | None = api_field(
        description="The map's alias, null when it has none.", example="Data center"
    )
    object_ids: list[str] = api_field(
        description="Ids of the map objects using the image as their icon.", example=[]
    )
    is_background: bool = api_field(description="Whether the map uses the image as its background.")


@api_model
class MapsImageUsageResponse:
    usage: list[MapsImageUsage] = api_field(
        description="Maps the caller may see that reference the image.", example=[]
    )


@api_model
class MapsAuthoringSettings:
    """The map/object authoring defaults the SPA's editor seeds new objects from.

    Flat by design: this mirrors ``cmk.maps.gui._settings.AuthoringDefaults``,
    which already unpacks the two nested FormSpec globals into the shape the
    editor works in. Only the two fields the flatten provably clamps are narrowed
    here — the rest stay plain strings because their FormSpec values reach the
    SPA unvalidated, and a Literal would promise a domain nothing enforces.
    """

    icon_size: int = api_field(description="Default icon edge length in pixels.", example=30)
    view_type: str = api_field(description="How a new object is drawn.", example="icon")
    url_target: str = api_field(
        description="Browsing context an object's link opens in.", example="_blank"
    )
    z: int = api_field(description="Default stacking order of a new object.", example=1)
    line_style: LineStyle = api_field(
        description="Default style for connection lines.", example="plain"
    )
    label_show: bool = api_field(description="Whether new objects carry a label.", example=True)
    label_size: int = api_field(description="Label font size in pixels.", example=11)
    label_color: str = api_field(description="Label text colour.", example="#ffffff")
    label_background: str = api_field(
        description="Label background colour, or ``transparent``.", example="transparent"
    )
    hover_template: str | None = api_field(
        description="Template for an object's hover card. Null when unset.", example=None
    )
    context_template: str | None = api_field(
        description="Template for an object's context menu. Null when unset.", example=None
    )
    default_backend_id: str = api_field(
        description="Connection a new map is bound to. Falls back to the local site's "
        "seeded connection.",
        example="cmk_heute",
    )
    default_map_type: str = api_field(description="Type a new map is created as.", example="static")
    default_render_mode: RenderMode = api_field(
        description="Rendering style a new map is created with.", example="default"
    )
    default_tile_url: str | None = api_field(
        description="Tile server for new worldmaps. Null for every other map type.",
        example=None,
    )
    map_list_view: MapListView = api_field(
        description="Site-wide default layout of the map overview. Each operator's own "
        "choice overrides this in the browser.",
        example="cards",
    )


@api_model
class MapsTileSource:
    """Where a geo map's tiles come from, and which servers the page allows.

    The browser fetches tiles straight from the tile server, so the maps page's
    content security policy decides which ones a geo map can reach. Both values
    are derived from the site's configuration, so the SPA does not mirror the
    policy or the built-in default in its own code.
    """

    default_url: str = api_field(
        description="Tile template a worldmap is drawn with when it sets none of its own.",
        example="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    )
    allowed_sources: list[str] = api_field(
        description="The tile servers the maps page allows the browser to fetch from. "
        "A map pointing anywhere else renders an empty canvas.",
        example=["https://tile.openstreetmap.org/"],
    )


@api_model
class MapsAuthoringSettingsResponse:
    settings: MapsAuthoringSettings = api_field(
        description="The site's effective authoring defaults."
    )
    tiles: MapsTileSource = api_field(description="The effective tile source for geo maps.")


@api_model
class MapsChoice:
    """One selectable entry (a contact group, a site) with its display name."""

    id: str = api_field(description="The entry's id.", example="all")
    alias: str = api_field(description="The entry's display name.", example="Everything")


@api_model
class MapsTicketCapabilities:
    """What the ticket's holder may do, resolved once by the GUI.

    The daemon reads the same set out of the signed ticket, so the SPA and the
    daemon never disagree about a caller's rights.
    """

    may_edit: bool = api_field(description="May create and edit own maps.")
    configure: bool = api_field(description="May administer Maps (images, settings).")
    see_all: bool = api_field(description="Bypasses the Livestatus contact-group scope.")
    folder_see_all: bool = api_field(description="Bypasses the Setup-folder read scope.")
    contact_groups: list[str] = api_field(
        description="The caller's contact groups.", example=["all"]
    )
    publish_all: bool = api_field(description="May publish a map to all users.")
    publish_to_groups: bool = api_field(description="May publish a map to contact groups.")
    publish_to_foreign_groups: bool = api_field(
        description="May publish a map to contact groups the caller is not in."
    )
    publish_to_sites: bool = api_field(description="May publish a map to specific sites.")
    all_contact_groups: list[MapsChoice] = api_field(
        description="Contact groups the access editor may offer.", example=[]
    )
    all_sites: list[MapsChoice] = api_field(
        description="Sites the access editor may offer.", example=[]
    )
    commands: list[CommandVerb] = api_field(
        description="The monitoring commands the caller may issue.", example=["acknowledge"]
    )


@api_model
class MapsTicketResponse:
    ticket: str = api_field(
        description="The signed, short-lived credential the daemon accepts.", example="eyJ0…"
    )
    stream_token: str | ApiOmitted = api_field(
        description=(
            "Reduced-capability, map-bound token for the event-stream URL. Present "
            "only for a map-scoped ticket -- the map list opens no stream."
        ),
        default_factory=ApiOmitted,
        example="eyJ0…",
    )
    user_id: str = api_field(description="The logged-in Checkmk user.", example="cmkadmin")
    language: str | None = api_field(
        description="The user's language, null when they follow the site default.",
        example="en",
    )
    capabilities: MapsTicketCapabilities = api_field(
        description="What this ticket grants, resolved from the user's permissions."
    )


@api_model
class MapsFormSchemaResponse:
    """A FormSpec rendered for the SPA, with its values in the form's own shape.

    ``data`` is not what is stored: a single-choice field carries an opaque id
    per element, and only the form spec's visitor knows which stored value each
    one stands for. The SPA hands its stored values in and gets them back
    encoded, rather than building the bag itself.
    """

    schema_: dict[str, object] = api_field(
        description="The form spec's component tree, as ``FormEdit`` consumes it.",
        serialization_alias="schema",
        example={},
    )
    data: dict[str, object] = api_field(
        description="The values to prefill the form with, in the form's own shape.",
        example={},
    )


@api_model
class MapsValidationMessage:
    location: list[str] = api_field(
        description="Path of the field the message belongs to.", example=["alias"]
    )
    message: str = api_field(
        description="What the form spec objected to.", example="The value must not be empty."
    )
    replacement_value: object = api_field(
        description="The value the form falls back to.", example=""
    )


@api_model
class MapsFormParseResponse:
    """The edited bag as it is stored, or what the form spec objected to.

    Validation messages are an answer rather than an error status: the dialog
    renders each one on the field that carries it, which a problem response
    could not address.
    """

    data: dict[str, object] | ApiOmitted = api_field(
        description="The values as they are stored. Absent when the form was rejected.",
        default_factory=ApiOmitted,
        example={},
    )
    validation: list[MapsValidationMessage] | ApiOmitted = api_field(
        description="What the form spec rejected. Absent when the values were accepted.",
        default_factory=ApiOmitted,
        example=[],
    )


@api_model
class MapsBackgroundResponse:
    filename: str = api_field(
        description=(
            "The stored background's file name, to be adopted as the map's "
            "``background_image``. It carries an unguessable token, so the "
            "statically served URL is a capability rather than a guessable path."
        ),
        example="6f1b…__datacenter.Zm9v.png",
    )


@api_model
class MapsCfgImportResponse:
    map_config: dict[str, object] = api_field(
        description="The parsed map, as a draft the editor shows before it is saved.",
        serialization_alias="map",
        example={},
    )
    warnings: list[str] = api_field(
        description="What the importer had to guess, in the operator's words.", example=[]
    )
