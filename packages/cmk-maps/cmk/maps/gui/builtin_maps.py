#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Built-in (shipped) maps — ready-to-use, operator-focused maps.

Mirrors ``cmk.gui.nonfree.pro.graphing._graph_collections``' ``builtin_pages``:
the entries are owned by :func:`UserId.builtin` and published, so every user who
may use Maps sees them. They open against the local site's own connection.

Only map types that auto-populate from live monitoring data are shipped
(Radar / Flow / Folder tree) — they show the real hosts, services and folders of
the site out of the box, no manual placement needed. The static / geo /
presentation types need hand-placed objects (or per-host geo labels) to be
meaningful, so they're left for users to author instead of shipped empty.
"""

from collections.abc import Mapping

from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId
from cmk.gui.i18n import _
from cmk.maps.gui.type_defs import map_config_from_spec, MapConfig, MapName
from cmk.maps.shared.map_payload import (
    DataElement,
    LabelAlign,
    LabelWeight,
    MapPayload,
    MapView,
    PresentationObjectType,
    PresentationView,
    TextElement,
)


def _builtin_map(name: MapName, alias: str, view: MapView, sort_order: int) -> MapConfig:
    map_spec: MapPayload = {
        # The map payload is a full MapConfig — every structural field the
        # map schema requires is present, so the map (de)serialises cleanly
        # through the REST show/list endpoints and the daemon register, not just
        # the visual envelope. ``name`` must match the visual name (the daemon
        # keys live state by it).
        "name": name,
        "alias": alias,
        # The local-site connection the sample config seeds (the daemon falls
        # back to the local site for any connection id it cannot resolve).
        "connection_id": f"cmk_{omd_site()}",
        "icon_size": None,
        "view": view,
        "objects": [],
        # Shipped reference maps: viewable by all, edited by cloning (like
        # built-in views/dashboards), never mutated in place.
        "readonly": True,
        "show_in_lists": True,
        "sort_order": sort_order,
        "version": 1,
        "render_mode": "default",
        "default_z": 1,
        "click_action": "link",
        "rotation_interval": 0,
    }
    # Built-in pagetypes are published to everyone (owner stays UserId.builtin()).
    return map_config_from_spec(UserId.builtin(), name, map_spec, public=True)


def _text_element(
    elem_id: str,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    z: int,
    text: str,
    font_size: float,
    font_weight: LabelWeight = "normal",
    text_align: LabelAlign = "center",
) -> TextElement:
    """A presentation text element with every required geometry/style field set."""
    return {
        "kind": "text",
        "id": elem_id,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "rotation": 0.0,
        "z": z,
        "opacity": 1.0,
        "locked": False,
        "hidden": False,
        "text": text,
        "font_size": font_size,
        "font_weight": font_weight,
        "font_style": "normal",
        "text_align": text_align,
        "line_height": 1.3,
        "letter_spacing": 0.0,
    }


def _data_tile(
    elem_id: str,
    *,
    x: float,
    z: int,
    object_type: PresentationObjectType,
    service_description: str | None,
    label: str,
) -> DataElement:
    """A presentation data tile (traffic-light gadget) with all required fields."""
    return {
        "kind": "data",
        "id": elem_id,
        "x": x,
        "y": 360,
        "w": 320,
        "h": 360,
        "rotation": 0.0,
        "z": z,
        "opacity": 1.0,
        "locked": False,
        "hidden": False,
        "only_hard_states": False,
        "auto_host": True,
        "object_type": object_type,
        "service_description": service_description,
        "display": {"mode": "gadget", "gadget_type": "trafficlight"},
        "label": {"show": True, "size": 16, "text": label},
    }


def _noc_wall_view() -> PresentationView:
    """A presentation NOC-wall starter, live on a fresh install.

    Presentation maps carry hand-placed elements (unlike the auto-populating
    types), but the data tiles use ``auto_host``: the daemon binds them to the
    site's primary host — the Checkmk server itself — at render time. So the
    wall shows the server's own health out of the box, and the operator can
    rebind any tile to another host or service.
    """
    # (label, object_type, service_description). The host tile always resolves;
    # the service tiles light up on the standard Checkmk-server services and
    # stay neutral placeholders on hosts that lack them.
    # Only the label is translated: the service description is a monitoring
    # identity that exists in exactly one spelling, so the tile keeps binding to
    # "CPU load" while its caption follows the operator's language. The two are
    # deliberately decoupled, not accidentally out of sync.
    tile_specs: list[tuple[str, PresentationObjectType, str | None]] = [
        (_("Checkmk server"), "host", None),
        (_("CPU load"), "service", "CPU load"),
        (_("Memory"), "service", "Memory"),
        (_("Root filesystem"), "service", "Filesystem /"),
    ]
    tiles = [
        _data_tile(
            f"tile_{i}",
            x=x,
            z=10 + i,
            object_type=obj_type,
            service_description=svc,
            label=label,
        )
        for i, (x, (label, obj_type, svc)) in enumerate(
            zip((160, 580, 1000, 1420), tile_specs, strict=True)
        )
    ]
    return {
        "type": "presentation",
        "width": 1920,
        "height": 1080,
        "theme": "midnight",
        "elements": [
            _text_element(
                "title",
                x=160,
                y=80,
                w=1600,
                h=90,
                z=1,
                text=_("NETWORK OPERATIONS"),
                font_size=64,
                font_weight="bold",
            ),
            _text_element(
                "subtitle",
                x=160,
                y=185,
                w=1600,
                h=40,
                z=2,
                text=_("Live infrastructure overview"),
                font_size=24,
            ),
            *tiles,
        ],
    }


def builtin_map_configs() -> Mapping[MapName, MapConfig]:
    """Return the shipped operator maps keyed by name (for ``MapPage.builtin_pages``)."""
    definitions: list[tuple[MapName, str, MapView]] = [
        # Every monitored host at a glance, colour-coded by worst state. Named
        # "Host radar" (not "All hosts") so the Monitor-menu entry stays distinct
        # from the built-in "All hosts" view — a shared label collides in the
        # navigation and reads as a duplicate to the operator.
        (
            "all_hosts",
            _("Host radar"),
            {"type": "radar", "filter": "all_hosts", "filter_value": ""},
        ),
        # Only the services currently in a problem state — the operator's triage
        # map. "Service problem radar" for the same reason (distinct from the
        # built-in "Service problems" view).
        (
            "service_problems",
            _("Service problem radar"),
            {"type": "radar", "filter": "all_services", "filter_value": "", "problems_only": True},
        ),
        # Parent/child topology auto-discovered from the site (NagVis-style automap).
        ("infrastructure", _("Infrastructure topology"), {"type": "flow"}),
        # The Setup folder hierarchy with live roll-up status per folder.
        ("monitoring_folders", _("Monitoring folders"), {"type": "foldertree"}),
        # Big-screen NOC wall starter (presentation type): a finished layout the
        # operator binds to real hosts/services.
        ("noc_wall", _("NOC wall"), _noc_wall_view()),
    ]
    return {
        name: _builtin_map(name, alias, view, sort_order)
        for sort_order, (name, alias, view) in enumerate(definitions)
    }
