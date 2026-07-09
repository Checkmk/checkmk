#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Maps-as-pagetypes storage, mirroring ``cmk.gui.nonfree.pro.graphing``.

Maps are Checkmk pagetypes: they live in the standard per-user pagetype store
(``var/check_mk/web/<user>/user_maps.mk``) via :meth:`MapPage.load` /
:meth:`MapPage.save_user_instances`, inheriting ownership, the publish/permission
model and Activate Changes replication — like graph collections. The list/edit UI
stays maps-own (the SPA); only the storage and permission plumbing is shared.
"""

import re
from pathlib import Path

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui import pagetypes
from cmk.gui.config import active_config
from cmk.gui.hooks import request_memoize
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import VisualPublic
from cmk.gui.utils.roles import UserPermissions
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.type_defs import map_config_from_spec, MapName, MapRead, MapSpec

# Map names are URL components and per-map permission idents (``map.<name>``), so
# keep them to the same safe charset the daemon enforces on map names.
_MAP_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,100}$")


def is_valid_map_name(name: str) -> bool:
    return bool(_MAP_NAME_RE.fullmatch(name))


@request_memoize()
def _user_permissions() -> UserPermissions:
    return UserPermissions.from_config(active_config, permission_registry)


@request_memoize()
def _instances() -> pagetypes.OverridableInstances[MapPage]:
    """Load all maps (built-ins + every user's) once per request."""
    return MapPage.load(_user_permissions())


def get_permitted_maps(user_permissions: UserPermissions | None = None) -> list[MapPage]:
    """The maps the user may see, with built-in/foreign shadowing.

    ``user_permissions`` defaults to the logged-in user's; callers that already
    resolved a permission set (e.g. the main-menu builder) pass it through so
    map visibility is computed against the same set as the rest of the menu.
    """
    return _instances().pages(user_permissions or _user_permissions())


def get_listable_maps(user_permissions: UserPermissions | None = None) -> list[MapPage]:
    """The maps to offer in lists and menus: permitted and not marked hidden.

    A map with ``show_in_lists`` unset stays fully usable by direct link, it is
    only kept out of the listings — so the filter belongs on the listing paths
    and not in :func:`get_permitted_maps`, whose other caller (the image usage
    scan) has to see every map that references an image.
    """
    return [page for page in get_permitted_maps(user_permissions) if not page.is_hidden()]


def get_permitted_map(name: MapName) -> MapPage | None:
    """The single map ``name`` resolves to for the logged-in user (or ``None``)."""
    return _instances().find_page(name, _user_permissions())


def get_own_map(owner: UserId, name: MapName) -> MapPage | None:
    """``owner``'s own stored map by name, regardless of visibility (or ``None``)."""
    instances = _instances()
    key = (owner, name)
    return instances.instance(key) if instances.has_instance(key) else None


def _user_maps_path(owner: UserId) -> Path:
    return cmk.utils.paths.profile_dir / owner / f"user_{MapPage.type_name()}s.mk"


def _own_instances(owner: UserId) -> pagetypes.OverridableInstances[MapPage]:
    """``owner``'s own stored maps, freshly loaded from disk.

    Handed to ``save_user_instances``, which rewrites a whole file from the set it
    gets — hence the fresh load inside each writer's lock. It is given *only* the
    owner's own pages on purpose: given every loaded page it would additionally
    rewrite every other owner's ``user_maps.mk`` (and, since built-ins carry the
    empty owner, a stray one beside the profile directories), files the lock taken
    here does not cover. Nothing is lost by leaving them out, because every writer
    below changes exactly one ``(owner, name)`` and ``owner`` is always the map's
    true owner.
    """
    own = pagetypes.OverridableInstances[MapPage]()
    for page in MapPage.load(_user_permissions()).instances():
        if page.owner() == owner:
            own.add_instance((owner, page.name()), page)
    return own


def create_map(
    owner: UserId, name: MapName, map_spec: MapSpec, public: VisualPublic | None
) -> bool:
    """Atomically create ``owner``'s map ``name``; return ``False`` if it already exists.

    A plain ``get_own_map`` check followed by :func:`save_map` is a check-then-write
    race: two concurrent creates of the same name both see it absent and the second
    silently overwrites the first. Serialize the existence check and the write under a
    file lock on the owner's pagetype store, reloading the instances fresh from disk
    inside the lock so a map that landed after this request's memoized load is still
    seen (see :func:`_own_instances` for what that set contains).

    This request's memoized set is updated too, for the same reason
    :func:`save_map` does it: the REST endpoint reads the map back right after
    creating it.
    """
    page = MapPage(map_config_from_spec(owner, name, map_spec, public))
    with store.locked(_user_maps_path(owner)):
        instances = _own_instances(owner)
        if instances.has_instance((owner, name)):
            return False
        instances.add_instance((owner, name), page)
        MapPage.save_user_instances(instances, _user_permissions(), owner)
    _instances().add_instance((owner, name), page)
    return True


def save_map(owner: UserId, name: MapName, map_spec: MapSpec, public: VisualPublic | None) -> None:
    """Persist ``map_spec`` as ``owner``'s map ``name`` with the given visibility.

    Locked and reloaded inside the lock for the same reason as :func:`create_map`:
    ``save_user_instances`` rewrites the owner's *whole* ``user_maps.mk`` from the
    instance set it is handed, so writing from the request-memoized (already
    stale) set would drop a map another request stored in the meantime.

    The request-memoized set is updated too, so a read later in *this* request
    (the REST update endpoint renders the saved map) sees the new state without
    re-reading the file.
    """
    page = MapPage(map_config_from_spec(owner, name, map_spec, public))
    with store.locked(_user_maps_path(owner)):
        instances = _own_instances(owner)
        instances.add_instance((owner, name), page)
        MapPage.save_user_instances(instances, _user_permissions(), owner)
    _instances().add_instance((owner, name), page)


def delete_map(owner: UserId, name: MapName) -> None:
    """Remove ``owner``'s map. No-op if it does not exist.

    Locked and reloaded like :func:`save_map` — a whole-file rewrite from a stale
    set would resurrect maps deleted, or drop maps saved, since this request
    loaded — and this request's memoized set is kept in sync as well.
    """
    with store.locked(_user_maps_path(owner)):
        instances = _own_instances(owner)
        if not instances.has_instance((owner, name)):
            return
        instances.remove_instance((owner, name))
        MapPage.save_user_instances(instances, _user_permissions(), owner)
    memoized = _instances()
    if memoized.has_instance((owner, name)):
        memoized.remove_instance((owner, name))


def _opt_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _opt_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _int(value: object, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def map_to_read(page: MapPage, can_edit: bool, can_delete: bool) -> MapRead:
    """Project a map to the SPA's light ``MapRead`` list shape.

    Reads the display fields from the opaque ``map_spec`` payload (a full
    MapConfig); the heavy ``objects`` list is intentionally dropped. ``can_edit``
    and ``can_delete`` are the pagetype authorization for this exact instance
    (``MapPage.may_edit``/``may_delete``), so built-ins and unauthorized foreign
    maps surface as read-only.
    """
    cfg = page.config
    payload = cfg.map_spec
    raw_view = payload.get("view")
    view = raw_view if isinstance(raw_view, dict) else {}
    return MapRead(
        name=cfg.name,
        alias=str(payload.get("alias") or cfg.name),
        background_image=_opt_str(payload.get("background_image")),
        background_color=_opt_str(payload.get("background_color")),
        icon_size=_opt_int(payload.get("icon_size")),
        connection_id=cfg.connection_id,
        view_type=cfg.map_type,
        view=view,
        object_count=cfg.object_count,
        rotation_interval=_int(payload.get("rotation_interval"), 0),
        version=_int(payload.get("version"), 0),
        sort_order=_int(payload.get("sort_order"), 0),
        click_action=str(payload.get("click_action") or "link"),
        readonly=bool(payload.get("readonly", False)),
        show_in_lists=bool(payload.get("show_in_lists", True)),
        hover_template=_opt_str(payload.get("hover_template")),
        context_template=_opt_str(payload.get("context_template")),
        render_mode=str(payload.get("render_mode") or "default"),
        default_z=_int(payload.get("default_z"), 1),
        can_edit=can_edit,
        can_delete=can_delete,
        owner=str(cfg.owner),
        is_builtin=page.is_builtin(),
        public=cfg.public,
    )
