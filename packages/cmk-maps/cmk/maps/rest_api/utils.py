#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared helpers for the Maps REST-API endpoints.

The map shape is validated by the Maps daemon (``MapConfig`` in
``cmk.maps.backend``); here we only (de)serialize between the REST ``@api_model``
mirror and the opaque ``map_spec`` dict that the pagetype store persists.
"""

import json
from collections.abc import Callable, Mapping

from pydantic import TypeAdapter, ValidationError

from cmk.gui.openapi.framework import EndpointBehavior, ETag
from cmk.gui.openapi.framework.model import json_dump_without_omitted
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException
from cmk.gui.type_defs import VisualPublic
from cmk.maps.gui._tickets import sign_map_config
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.store import get_permitted_map
from cmk.maps.gui.type_defs import MapName
from cmk.maps.rest_api.models.map import (
    MapConfig,
    MapListEntry,
    MapView,
)
from cmk.maps.rest_api.models.response_models import (
    MapExtensions,
    MapListExtensions,
    MapListObject,
    MapObject,
    MapVisibility,
)
from cmk.maps.shared.map_payload import ClickAction, RenderMode
from cmk.web.utils import permission_verification as permissions

# Resolving which maps the user may see checks for the other users' maps
# (``general.see_user_map``), for the user's own (``general.edit_map``), the
# forced ones (``general.force_map``) and the per-instance ``map.<name>`` grant
# that built-in and published maps register. Each is branched on rather than
# required, so all are declared ``Optional``.
MAP_VISIBILITY_PERMISSIONS: list[permissions.BasePerm] = [
    permissions.Optional(permissions.Perm("general.see_user_map")),
    permissions.Optional(permissions.Perm("general.edit_map")),
    permissions.Optional(permissions.Perm("general.force_map")),
    permissions.PrefixPerm("map"),
]
# ``may_edit`` adds ``general.edit_foreign_map`` for a foreign map.
MAP_EDIT_PERMISSIONS: list[permissions.BasePerm] = [
    permissions.Optional(permissions.Perm("general.edit_foreign_map")),
]

# Maps are pagetypes, so read *and* write touch the generic pagetype permissions:
# every serialization stamps ``can_edit``/``can_delete`` (``may_delete`` adds
# ``general.delete_foreign_map``), and writes additionally go through the publish
# gates. The framework's permission tracker raises as soon as a *checked*
# permission is not declared here (even a foreign map merely serialized in a
# list), so every branch must be represented.
_PAGETYPE_PERMISSIONS: list[permissions.BasePerm] = [
    *MAP_EDIT_PERMISSIONS,
    permissions.Optional(permissions.Perm("general.delete_foreign_map")),
    permissions.Optional(permissions.Perm("general.publish_map")),
    permissions.Optional(permissions.Perm("general.publish_to_groups_map")),
    permissions.Optional(permissions.Perm("general.publish_to_foreign_groups_map")),
    permissions.Optional(permissions.Perm("general.publish_to_sites_map")),
    *MAP_VISIBILITY_PERMISSIONS,
]
PERMISSIONS = permissions.AllPerm([permissions.Perm("maps.use"), *_PAGETYPE_PERMISSIONS])
RW_PERMISSIONS = PERMISSIONS

# ``sites.live()`` widens the connection's scope with each of these, so every
# endpoint opening one checks them. The two component permissions are absent
# from editions without the component.
LIVESTATUS_PERMISSIONS: list[permissions.BasePerm] = [
    permissions.Optional(permissions.Perm("general.see_all")),
    permissions.Optional(permissions.OkayToIgnorePerm("bi.see_all")),
    permissions.Optional(permissions.OkayToIgnorePerm("mkeventd.seeall")),
]

# For every endpoint that touches no configuration file: a read, a livestatus
# command, or a write under ``var/maps``. None of them belongs behind the Setup
# lock, and none of them is a pending change.
NO_CONFIG_CHANGE = EndpointBehavior(skip_locking=True, update_config_generation=False)

_MAP_ADAPTER: TypeAdapter[MapConfig] = TypeAdapter(MapConfig)
# The light list projection parses only the (small) ``view`` block, not the
# heavy ``objects`` list, so listing stays cheap on sites with many maps.
_MAP_VIEW_ADAPTER: TypeAdapter[MapView] = TypeAdapter(MapView)

# --------------------------------------------------------------------------- #
# Grouped-API <-> flat-store bridge                                           #
#                                                                             #
# The stored ``map_spec`` (validated by the daemon) is FLAT; the REST model   #
# groups the object fields into nested sub-objects for a more intuitive API   #
# (the Checkmk ``from_internal``/``to_internal`` convention). These tables    #
# and helpers translate between the two shapes at the endpoint boundary.      #
# Each entry maps ``rest_field -> stored_flat_key``; ``label`` and ``display``#
# are already stored as nested dicts and are handled separately below.        #
# --------------------------------------------------------------------------- #

_OBJECT_GROUPS: dict[str, dict[str, str]] = {
    "position": {"x": "x", "y": "y", "z": "z", "lat": "lat", "lng": "lng"},
    "link": {
        "url_target": "url_target",
        "url": "url",
        "hover_url": "hover_url",
        "hover_template": "hover_template",
        "context_template": "context_template",
    },
    "binding": {
        "connection_id": "connection_id",
        "host_name": "host_name",
        "service_description": "service_description",
        "group_name": "group_name",
        "map_name": "map_name",
        "aggregation_id": "aggregation_id",
        "object_types": "object_types",
        "object_filter": "object_filter",
        "only_hard_states": "only_hard_states",
        "recognize_services": "recognize_services",
        "expand_depth": "expand_depth",
    },
    "cmk_label": {
        "name": "cmk_label_name",
        "value": "cmk_label_value",
        "target": "cmk_label_target",
    },
    "bundle": {"kind": "bundle_kind", "hosts": "bundle_hosts", "precision": "bundle_precision"},
    "line": {
        "x2": "x2",
        "y2": "y2",
        "lat2": "lat2",
        "lng2": "lng2",
        "mid_x": "mid_x",
        "mid_y": "mid_y",
        "start_ref": "start_ref",
        "end_ref": "end_ref",
        "style": "line_style",
        "width": "line_width",
        "perfdata_label": "line_perfdata_label",
        "weather_color": "line_weather_color",
        "metric_in": "weathermap_metric",
        "metric_out": "weathermap_metric_out",
        "color": "line_color",
        "color_border": "line_color_border",
    },
    "textbox": {
        "background": "textbox_background",
        "border": "textbox_border",
        "width": "textbox_width",
        "height": "textbox_height",
    },
    "graph": {
        "url": "graph_url",
        "embed_type": "graph_embed_type",
        "width": "graph_width",
        "height": "graph_height",
        "refresh_interval": "graph_refresh_interval",
        "metric": "graph_metric",
        "id": "graph_id",
        "time_window": "graph_time_window",
    },
    "filter": {
        "exclude_members": "exclude_members",
        "exclude_member_states": "exclude_member_states",
    },
}
# Groups that are always present because their stored keys are required on every
# object (the daemon has no default for them), so the nested sub-object is never
# omitted even when only its required members are set.
_REQUIRED_OBJECT_GROUPS = ("position", "link")
# Label config fields living inside the stored ``label`` sub-dict (everything on
# the REST ``label`` group except the two that map to top-level flat keys).
_LABEL_EXTRAS = {"border": "label_border", "max_length": "label_maxlen"}
# Shared geometry hoisted into the presentation element ``transform`` sub-object.
_TRANSFORM_FIELDS = ("x", "y", "w", "h", "rotation", "z", "opacity", "locked", "hidden")


def _sub_mapping(value: object) -> Mapping[str, object]:
    """A nested JSON sub-object, or an empty mapping for anything else."""
    return value if isinstance(value, Mapping) else {}


def _nest_object(flat: Mapping[str, object]) -> dict[str, object]:
    nested: dict[str, object] = {"id": flat.get("id"), "type": flat.get("type")}
    for group, fields in _OBJECT_GROUPS.items():
        sub = {rest: flat[stored] for rest, stored in fields.items() if stored in flat}
        if sub or group in _REQUIRED_OBJECT_GROUPS:
            nested[group] = sub
    if "image_src" in flat:
        nested["image_src"] = flat["image_src"]
    if isinstance(display := flat.get("display"), dict):
        nested["display"] = dict(display)
    label = dict(_sub_mapping(flat.get("label")))
    for rest, stored in _LABEL_EXTRAS.items():
        if stored in flat:
            label[rest] = flat[stored]
    if label:
        nested["label"] = label
    return nested


def _flatten_object(nested: Mapping[str, object]) -> dict[str, object]:
    flat: dict[str, object] = {"id": nested.get("id"), "type": nested.get("type")}
    for group, fields in _OBJECT_GROUPS.items():
        sub = _sub_mapping(nested.get(group))
        for rest, stored in fields.items():
            if rest in sub:
                flat[stored] = sub[rest]
    if "image_src" in nested:
        flat["image_src"] = nested["image_src"]
    if isinstance(display := nested.get("display"), dict):
        flat["display"] = dict(display)
    label = dict(_sub_mapping(nested.get("label")))
    for rest, stored in _LABEL_EXTRAS.items():
        if rest in label:
            flat[stored] = label.pop(rest)
    if label:
        flat["label"] = label
    return flat


def _nest_element(flat: Mapping[str, object]) -> dict[str, object]:
    nested: dict[str, object] = {k: v for k, v in flat.items() if k not in _TRANSFORM_FIELDS}
    nested["transform"] = {k: flat[k] for k in _TRANSFORM_FIELDS if k in flat}
    return nested


def _flatten_element(nested: Mapping[str, object]) -> dict[str, object]:
    flat: dict[str, object] = {k: v for k, v in nested.items() if k != "transform"}
    flat.update(_sub_mapping(nested.get("transform")))
    return flat


def _elements(view: Mapping[str, object]) -> list[object] | None:
    """The presentation elements to (un)nest, or None for any other view type."""
    elements = view.get("elements")
    if view.get("type") != "presentation" or not isinstance(elements, list):
        return None
    return elements


def _nest_view(view: Mapping[str, object]) -> dict[str, object]:
    result = dict(view)
    if (elements := _elements(result)) is not None:
        result["elements"] = [_nest_element(_sub_mapping(e)) for e in elements]
    return result


def _flatten_view(view: Mapping[str, object]) -> dict[str, object]:
    result = dict(view)
    if (elements := _elements(result)) is not None:
        result["elements"] = [_flatten_element(_sub_mapping(e)) for e in elements]
    return result


def map_from_spec(spec: Mapping[str, object]) -> MapConfig:
    """Validate a stored (flat) ``map_spec`` dict into the typed, grouped map model."""
    prepared = dict(spec)
    if isinstance(objects := prepared.get("objects"), list):
        prepared["objects"] = [_nest_object(_sub_mapping(o)) for o in objects]
    if isinstance(view := prepared.get("view"), dict):
        prepared["view"] = _nest_view(view)
    return _MAP_ADAPTER.validate_python(prepared)


def spec_from_map(map_cfg: MapConfig) -> dict[str, object]:
    """Serialize a typed, grouped map back to the flat ``map_spec`` dict for storage."""
    nested: dict[str, object] = json.loads(json_dump_without_omitted(MapConfig, map_cfg))
    if isinstance(objects := nested.get("objects"), list):
        nested["objects"] = [_flatten_object(_sub_mapping(o)) for o in objects]
    if isinstance(view := nested.get("view"), dict):
        nested["view"] = _flatten_view(view)
    return nested


def visibility_from_public(public: VisualPublic | None) -> MapVisibility:
    if public is True:
        return MapVisibility(publish="all")
    if isinstance(public, tuple) and public[0] in ("contact_groups", "sites"):
        return MapVisibility(publish=public[0], groups=list(public[1]))
    return MapVisibility(publish="private")


def validate_visibility(visibility: MapVisibility) -> None:
    """Reject a share scope that names no targets.

    ``publish=contact_groups``/``sites`` with an empty/omitted ``groups`` would
    otherwise clamp silently to private (an empty allowed set), hiding the caller's
    mistake behind a surprising scope downgrade — make it an explicit 400 instead."""
    if visibility.publish in ("contact_groups", "sites"):
        groups = visibility.groups if isinstance(visibility.groups, list) else []
        if not groups:
            raise RestAPIRequestGeneralException(
                status=400,
                title="Missing share targets",
                detail=f"Sharing to {visibility.publish!r} requires at least one entry in 'groups'.",
            )


def public_request_from_visibility(visibility: MapVisibility) -> VisualPublic:
    """The *requested* visibility, pre-clamp. Callers must still run it through
    ``cmk.maps.gui._pages._authorized_public`` to enforce publish permissions."""
    if visibility.publish == "all":
        return True
    if visibility.publish in ("contact_groups", "sites"):
        groups = visibility.groups if isinstance(visibility.groups, list) else []
        return (visibility.publish, groups)
    return False


def _public_key(public: VisualPublic | None) -> object:
    if isinstance(public, tuple):
        return [public[0], list(public[1])]
    return public


def _opt_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _opt_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _int(value: object, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _render_mode(value: object) -> RenderMode:
    return "nagvis_classic" if value == "nagvis_classic" else "default"


def _click_action(value: object) -> ClickAction:
    return "none" if value == "none" else "link"


def _list_view(value: object) -> MapView:
    """Parse a stored ``view`` into the typed union for the list projection.

    A single map with a view the union can't represent (a legacy / imported
    ``type``, or a half-written spec) must not 500 the whole collection, so fall
    back to an empty static view — matching the tolerant raw-dict passthrough of
    the page-hydrated home list (``store.map_to_read``)."""
    try:
        prepared = _nest_view(value) if isinstance(value, dict) and value else {"type": "static"}
        return _MAP_VIEW_ADAPTER.validate_python(prepared)
    except ValidationError:
        return _MAP_VIEW_ADAPTER.validate_python({"type": "static"})


def map_etag(page: MapPage) -> ETag:
    cfg = page.config
    return ETag(
        {
            "name": cfg.name,
            "owner": str(cfg.owner),
            "public": _public_key(cfg.public),
            "spec": dict(cfg.map_spec),
        }
    )


def resolve_map_link_titles(
    spec: Mapping[str, object], lookup: Callable[[MapName], MapPage | None]
) -> dict[str, str]:
    """The titles of the maps this map links to, keyed by map name.

    A link stores only its target's name, and that name is an id — a URL segment
    and the ``map.<name>`` permission ident — so it reads nothing like the title
    the operator picked the link by.

    ``lookup`` decides visibility, and only the GUI can: a map the user may not
    see, or one that is gone, is left out, and the caption falls back to the name.
    """
    objects = spec.get("objects")
    if not isinstance(objects, list):
        return {}
    linked: set[str] = set()
    for obj in objects:
        if not isinstance(obj, dict) or obj.get("type") != "map":
            continue
        name = obj.get("map_name")
        if isinstance(name, str) and name:
            linked.add(name)
    titles: dict[str, str] = {}
    for name in linked:
        if (target := lookup(name)) is not None:
            titles[name] = target.config.title or target.config.name
    return titles


def serialize_map(page: MapPage, *, can_edit: bool, can_delete: bool) -> MapObject:
    cfg = page.config
    # Fold the authoritative pagetype name into the config, exactly as the GUI
    # ``_pages._signed_map`` path does, so a stored spec whose ``name`` drifted
    # from the pagetype key (a clone/rename/migration) can't be signed — and thus
    # relayed to the daemon — under a foreign map name.
    spec = {**dict(cfg.map_spec), "name": cfg.name}
    # Sign the resolved config so the SPA can relay {config_b64, sig} to the Maps
    # daemon's register endpoint (verified there against the ticket's owner) — the
    # same bytes the daemon renders.
    signed = sign_map_config(spec, owner=str(cfg.owner))
    return MapObject(
        domainType="map",
        id=cfg.name,
        title=cfg.title or cfg.name,
        extensions=MapExtensions(
            owner=str(cfg.owner),
            visibility=visibility_from_public(cfg.public),
            is_builtin=page.is_builtin(),
            can_edit=can_edit,
            can_delete=can_delete,
            config=map_from_spec(spec),
            config_b64=signed["config_b64"],
            sig=signed["sig"],
            # Beside the signed bytes, not inside them: the titles are resolved
            # per requesting user, the signature covers the stored config.
            map_link_titles=resolve_map_link_titles(spec, get_permitted_map),
        ),
        links=[LinkModel.create("self", object_href("map", cfg.name))],
    )


def serialize_map_list_entry(page: MapPage, *, can_edit: bool, can_delete: bool) -> MapListObject:
    cfg = page.config
    payload = cfg.map_spec
    summary = MapListEntry(
        name=cfg.name,
        alias=str(payload.get("alias") or cfg.name),
        connection_id=cfg.connection_id,
        view_type=cfg.map_type,
        view=_list_view(payload.get("view")),
        click_action=_click_action(payload.get("click_action")),
        object_count=cfg.object_count,
        background_image=_opt_str(payload.get("background_image")),
        background_color=_opt_str(payload.get("background_color")),
        icon_size=_opt_int(payload.get("icon_size")),
        rotation_interval=_int(payload.get("rotation_interval"), 0),
        sort_order=_int(payload.get("sort_order"), 0),
        version=_int(payload.get("version"), 0),
        show_in_lists=bool(payload.get("show_in_lists", True)),
        render_mode=_render_mode(payload.get("render_mode")),
        readonly=bool(payload.get("readonly", False)),
        hover_template=_opt_str(payload.get("hover_template")),
        context_template=_opt_str(payload.get("context_template")),
        default_z=_int(payload.get("default_z"), 1),
    )
    return MapListObject(
        domainType="map",
        id=cfg.name,
        title=cfg.title or cfg.name,
        extensions=MapListExtensions(
            owner=str(cfg.owner),
            visibility=visibility_from_public(cfg.public),
            is_builtin=page.is_builtin(),
            can_edit=can_edit,
            can_delete=can_delete,
            summary=summary,
        ),
        links=[LinkModel.create("self", object_href("map", cfg.name))],
    )
