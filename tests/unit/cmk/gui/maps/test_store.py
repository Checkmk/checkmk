#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the maps-as-pagetypes storage (standard per-user pagetype store)."""

import pytest

import cmk.utils.paths
from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.maps.gui import store
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.type_defs import map_config_from_spec


def _user_permissions() -> UserPermissions:
    return UserPermissions.from_config(active_config, permission_registry)


def _map(name: str, alias: str = "My map") -> dict[str, object]:
    return {
        "name": name,
        "alias": alias,
        "connection_id": "cmk_heute",
        "objects": [{"id": "o1"}, {"id": "o2"}],
        "view": {"type": "flow"},
    }


def test_save_and_reload_round_trip(
    request_context: None,  # noqa: ARG001
    with_admin_login: UserId,
) -> None:
    owner = with_admin_login
    store.save_map(owner, "map1", _map("map1"), public=False)

    # A fresh load reads it back from disk (bypassing the request-memoized
    # instances).
    reloaded = MapPage.load(_user_permissions())
    assert reloaded.has_instance((owner, "map1"))
    page = reloaded.instance((owner, "map1"))
    assert page.config.map_spec["objects"] == [{"id": "o1"}, {"id": "o2"}]
    # The owner sees it via the permission path.
    assert any(p.name() == "map1" for p in reloaded.pages(_user_permissions()))


@pytest.mark.parametrize("mutate", ["save", "delete"])
def test_write_does_not_drop_a_map_stored_after_the_memoized_load(
    request_context: None,  # noqa: ARG001
    with_admin_login: UserId,
    mutate: str,
) -> None:
    """A write must not rewrite the store from this request's stale instance set.

    ``save_user_instances`` rewrites the owner's whole ``user_maps.mk``, so a write
    built on the request-memoized load would silently drop everything another
    request stored in between. Simulated deterministically: memoize the load, then
    write a map behind its back.
    """
    owner = with_admin_login
    store.save_map(owner, "first", _map("first"), public=False)
    # Memoize this request's instance set (it now contains "first" only)...
    store.get_permitted_maps()
    # ...then let a concurrent request store another map straight to disk.
    concurrent = MapPage.load(_user_permissions())
    concurrent.add_instance(
        (owner, "second"), MapPage(map_config_from_spec(owner, "second", _map("second")))
    )
    MapPage.save_user_instances(concurrent, _user_permissions(), owner)

    if mutate == "save":
        store.save_map(owner, "third", _map("third"), public=False)
    else:
        store.delete_map(owner, "first")

    on_disk = MapPage.load(_user_permissions())
    assert on_disk.has_instance((owner, "second")), "the concurrently stored map was lost"


def test_empty_store_has_builtin_maps(
    request_context: None,  # noqa: ARG001
    with_admin_login: UserId,  # noqa: ARG001
) -> None:
    # The user has saved no maps; only the shipped built-in example maps
    # (owner = builtin) remain in the permitted set.
    permitted = store.get_permitted_maps()
    assert permitted, "built-in example maps should always be present"
    assert all(page.is_builtin() for page in permitted)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("ok_name-1", True),
        ("", False),
        ("../escape", False),
        ("with space", False),
        ("a" * 100, True),
        ("a" * 101, False),
    ],
)
def test_is_valid_map_name(name: str, expected: bool) -> None:
    assert store.is_valid_map_name(name) is expected


def test_map_config_from_spec_derives_light_fields() -> None:
    owner = UserId("alice")
    map_spec = {
        "alias": "Network overview",
        "connection_id": "cmk_heute",
        "objects": [{"id": "o1"}, {"id": "o2"}, {"id": "o3"}],
        "view": {"type": "worldmap"},
    }
    cfg = map_config_from_spec(owner, "net", map_spec)
    assert cfg.owner == owner
    assert cfg.name == "net"
    assert cfg.title == "Network overview"
    assert cfg.map_type == "worldmap"
    assert cfg.connection_id == "cmk_heute"
    assert cfg.object_count == 3
    assert cfg.public is False
    assert cfg.map_spec is map_spec


def test_map_config_from_spec_presentation_counts_elements() -> None:
    map_spec = {"view": {"type": "presentation", "elements": [{"a": 1}, {"a": 2}]}}
    cfg = map_config_from_spec(UserId("bob"), "pres", map_spec)
    assert cfg.object_count == 2
    assert cfg.title == "pres"  # falls back to the name when no alias


def test_map_to_read_projects_light_shape() -> None:
    map_spec = {
        "alias": "Net",
        "connection_id": "cmk_heute",
        "view": {"type": "worldmap", "lat": 1.0},
        "objects": [{"id": "o1"}],
        "render_mode": "nagvis_classic",
        "rotation_interval": 30,
    }
    page = MapPage(map_config_from_spec(UserId("alice"), "net", map_spec))
    read = store.map_to_read(page, can_edit=True, can_delete=True)
    assert read["name"] == "net"
    assert read["view_type"] == "worldmap"
    assert read["object_count"] == 1
    assert read["render_mode"] == "nagvis_classic"
    assert read["rotation_interval"] == 30
    assert read["can_edit"] is True
    assert read["can_delete"] is True
    assert "objects" not in read  # heavy payload dropped from the list shape


def test_delete_map_round_trip(
    request_context: None,  # noqa: ARG001
    with_admin_login: UserId,
) -> None:
    owner = with_admin_login
    store.save_map(owner, "map1", _map("map1"), public=False)
    assert MapPage.load(_user_permissions()).has_instance((owner, "map1"))

    store.delete_map(owner, "map1")
    assert not MapPage.load(_user_permissions()).has_instance((owner, "map1"))


def test_map_hidden_from_the_menu_stays_permitted(
    request_context: None,  # noqa: ARG001
    with_admin_login: UserId,
) -> None:
    """Hidden from the Monitor menu means "not linked there", not "not accessible".

    Only the menu goes through ``get_menu_maps``; the maps overview and the
    image usage scan see every permitted map.
    """
    owner = with_admin_login
    store.save_map(owner, "shown", _map("shown"), public=False)
    store.save_map(owner, "hidden", _map("hidden"), public=False, hidden=True)

    assert "hidden" not in {page.name() for page in store.get_menu_maps()}
    assert "shown" in {page.name() for page in store.get_menu_maps()}
    assert "hidden" in {page.name() for page in store.get_permitted_maps()}
    # Still reachable by direct link.
    assert store.get_permitted_map("hidden") is not None


def test_created_map_is_readable_through_the_memoized_instances(
    request_context: None,  # noqa: ARG001
    with_admin_login: UserId,
) -> None:
    """The REST create endpoint reads the map back right after creating it.

    Materialize the request-memoized instances *before* creating, the way any
    earlier map read in the same request does, so the read afterwards cannot be
    served by a fresh load from disk.
    """
    owner = with_admin_login
    store.get_permitted_maps()

    assert store.create_map(owner, "map1", _map("map1"), public=False)

    assert store.get_own_map(owner, "map1") is not None


def test_writing_a_map_touches_only_the_owners_file(
    request_context: None,  # noqa: ARG001
    with_admin_login: UserId,
) -> None:
    """``save_user_instances`` rewrites every file in the set it is handed.

    Given the full instance set it also rewrites every *other* owner's
    ``user_maps.mk`` — which the writer's lock does not cover — and a stray
    ``user_maps.mk`` beside the profile directories, because built-in pagetypes
    carry the empty owner. Only the owner's own file may be written.
    """
    other = UserId("other-user")
    store.save_map(other, "theirs", _map("theirs"), public=False)

    store.save_map(with_admin_login, "mine", _map("mine"), public=False)

    written = {
        str(path.relative_to(cmk.utils.paths.profile_dir))
        for path in cmk.utils.paths.profile_dir.rglob("user_maps.mk")
    }
    assert written == {f"{with_admin_login}/user_maps.mk", f"{other}/user_maps.mk"}
