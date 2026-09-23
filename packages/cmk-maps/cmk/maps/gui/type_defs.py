#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Type definitions for maps stored as Checkmk pagetypes."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.ccc.user import UserId
from cmk.gui import pagetypes
from cmk.gui.type_defs import VisualPublic

MapName = str

# The full map payload: placed objects plus view geometry (flow positions,
# presentation elements, …). The GUI treats it opaquely — only the Maps daemon
# validates its shape (cmk.maps.backend.schemas.map.MapConfig).
MapSpec = Mapping[str, object]


class MapModel(pagetypes.OverridableModel):
    """On-disk shape of a map (``var/check_mk/web/<user>/user_maps.mk``)."""

    # Map renderer: flow / worldmap / radar / static / foldertree.
    map_type: str
    connection_id: str
    # Number of placed objects — shown as a list column.
    object_count: int
    map_spec: MapSpec


@dataclass(kw_only=True)
class MapConfig(pagetypes.OverridableConfig):
    """A map stored as a Checkmk pagetype.

    The whole map lives in the standard per-user pagetype store
    (``var/check_mk/web/<user>/user_maps.mk``) and inherits ownership, the
    publish/permission model and Activate Changes replication — like graph
    collections. The light fields back the Customize list columns; ``map_spec``
    carries the full payload the SPA renders.
    """

    map_type: str
    connection_id: str
    object_count: int
    map_spec: MapSpec


class MapRead(TypedDict):
    """The light list projection of a map — what the SPA renders in the overview.

    Mirrors the REST ``MapListEntry`` summary, minus the heavy ``objects`` list.
    ``view`` stays opaque (the daemon validates the payload shape, not the GUI);
    everything the list actually renders is spelled out.
    """

    name: MapName
    alias: str
    background_image: str | None
    background_color: str | None
    icon_size: int | None
    connection_id: str
    view_type: str
    view: Mapping[str, object]
    object_count: int
    rotation_interval: int
    version: int
    sort_order: int
    click_action: str
    hide_in_monitor_menu: bool
    hover_template: str | None
    context_template: str | None
    render_mode: str
    default_z: int
    can_edit: bool
    can_delete: bool
    owner: str
    is_builtin: bool
    # The raw VisualPublic: False (private), True (published to all), or
    # ("contact_groups"|"sites", [...]). None on a config that never set it.
    public: VisualPublic | None


def map_config_from_spec(
    owner: UserId,
    name: MapName,
    map_spec: MapSpec,
    public: VisualPublic | None = False,
    hidden: bool = False,
) -> MapConfig:
    """Wrap a map payload in the pagetype envelope owned by ``owner``.

    The heavy payload is stored opaquely under ``map_spec``; the light fields are
    derived best-effort for the Customize list columns (the payload stays the
    source of truth — the daemon validates its shape, not the GUI).

    ``public`` is a parameter rather than a post-construction assignment so a
    caller cannot forget it: the private default is only right for a caller that
    has no visibility to carry, and silently un-publishing a shipped built-in map
    would be invisible until someone missed it in the list. ``hidden`` (left out
    of the Monitor menu) is envelope state for the same reason, not payload.
    """
    view = map_spec.get("view")
    view_dict = view if isinstance(view, dict) else {}
    # Object maps carry ``objects``; presentation maps carry ``view.elements``.
    # The two are mutually exclusive by map type — count whichever is populated
    # (``objects`` wins) rather than summing, so a map that happens to carry both
    # is not double-counted in the Customize list column.
    objects = map_spec.get("objects")
    elements = view_dict.get("elements")
    n_objects = len(objects) if isinstance(objects, list) else 0
    n_elements = len(elements) if isinstance(elements, list) else 0
    object_count = n_objects or n_elements
    return MapConfig(
        owner=owner,
        name=name,
        title=str(map_spec.get("alias") or name),
        description="",
        hidden=hidden,
        public=public,
        map_type=str(view_dict.get("type", "static")),
        connection_id=str(map_spec.get("connection_id", "")),
        object_count=object_count,
        map_spec=map_spec,
    )
