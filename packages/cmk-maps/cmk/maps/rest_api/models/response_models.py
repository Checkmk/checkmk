#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)
from cmk.maps.rest_api.models.map import MapConfig, MapListEntry


@api_model
class MapVisibility:
    """A map's sharing scope (the pagetype ``public`` envelope, not the map)."""

    publish: Literal["private", "all", "contact_groups", "sites"] = api_field(
        description="Who may see this map: only the owner (private), everyone (all), "
        "or members of the listed contact groups / sites.",
    )
    groups: list[str] | ApiOmitted = api_field(
        description="Contact-group or site ids the map is shared with "
        "(only for publish=contact_groups/sites).",
        default_factory=ApiOmitted,
    )


@api_model
class MapExtensions:
    owner: str = api_field(description="User id that owns this map ('' for built-ins).")
    visibility: MapVisibility = api_field(description="The map's sharing scope.")
    is_builtin: bool = api_field(description="Whether this is a shipped built-in map.")
    can_edit: bool = api_field(description="Whether the requesting user may edit this map.")
    can_delete: bool = api_field(description="Whether the requesting user may delete this map.")
    config: MapConfig = api_field(description="The full map configuration.")
    config_b64: str = api_field(
        description="The map config as canonically-serialized base64url bytes, "
        "GUI-signed for the Maps daemon (relay verbatim to the register endpoint)."
    )
    sig: str = api_field(
        description="HMAC signature over ``config_b64`` the Maps daemon verifies "
        "before trusting the config for its live-state broadcast."
    )
    map_link_titles: dict[str, str] = api_field(
        description="Titles of the maps this map links to, keyed by map id. A map "
        "link stores only the target's id; this resolves the title to caption it "
        "with. Only maps the requesting user may see appear here.",
    )


@api_model
class MapObject(DomainObjectModel):
    domainType: Literal["map"] = api_field(description="The domain type of the object.")
    extensions: MapExtensions = api_field(description="The map's attributes and map payload.")


@api_model
class MapListExtensions:
    owner: str = api_field(description="User id that owns this map ('' for built-ins).")
    visibility: MapVisibility = api_field(description="The map's sharing scope.")
    is_builtin: bool = api_field(description="Whether this is a shipped built-in map.")
    can_edit: bool = api_field(description="Whether the requesting user may edit this map.")
    can_delete: bool = api_field(description="Whether the requesting user may delete this map.")
    summary: MapListEntry = api_field(description="Light map metadata (no objects).")


@api_model
class MapListObject(DomainObjectModel):
    domainType: Literal["map"] = api_field(description="The domain type of the object.")
    extensions: MapListExtensions = api_field(description="The map's list attributes.")


@api_model
class MapCollection(DomainObjectCollectionModel):
    domainType: Literal["map"] = api_field(
        description="The domain type of the objects in the collection."
    )
    value: list[MapListObject] = api_field(description="A list of maps.")
