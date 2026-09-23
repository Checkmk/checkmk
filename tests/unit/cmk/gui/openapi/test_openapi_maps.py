#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""End-to-end CRUD behavior tests for the Maps REST-API endpoints.

Exercises the endpoints through the real WSGI app + pagetype store (create →
show → list → update-with-ETag → delete), plus the error paths and a
discriminated-union round-trip, complementing the shape contract test
(``test_maps_map_contract``) which pins the schema against the daemon.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from cmk.ccc.user import UserId
from cmk.maps.rest_api import utils
from tests.testlib.unit.rest_api_client import ClientRegistry


def _map(name: str, **overrides: object) -> dict[str, object]:
    """A complete map payload — the REST model requires the structural fields."""
    map_spec: dict[str, object] = {
        "name": name,
        "alias": name.title(),
        "connection_id": "live_1",
        "icon_size": None,
        "rotation_interval": 0,
        "sort_order": 0,
        "click_action": "link",
        "view": {"type": "static"},
        "objects": [],
    }
    map_spec.update(overrides)
    return map_spec


def _host_object(
    obj_id: str,
    *,
    obj_type: str = "host",
    x: object = 10,
    y: object = 20,
    url_target: str = "_blank",
    **groups: object,
) -> dict[str, object]:
    # The REST object model is grouped: identity + the required ``position`` and
    # ``link`` sub-objects, plus per-concern groups (``binding``, ``line``, …)
    # passed through ``groups``.
    obj: dict[str, object] = {
        "id": obj_id,
        "type": obj_type,
        "position": {"x": x, "y": y},
        "link": {"url_target": url_target},
    }
    obj.update(groups)
    return obj


def _element(kind: str, elem_id: str, **overrides: object) -> dict[str, object]:
    elem: dict[str, object] = {
        "kind": kind,
        "id": elem_id,
        "transform": {
            "x": 0,
            "y": 0,
            "w": 120,
            "h": 80,
            "rotation": 0,
            "z": 0,
            "opacity": 1.0,
            "locked": False,
            "hidden": False,
        },
    }
    elem.update(overrides)
    return elem


_STATIC_MAP = _map(
    "map1",
    alias="Map One",
    view={"type": "static", "problems_only": True},
    objects=[_host_object("o1", binding={"host_name": "srv1"})],
)

_PRESENTATION_MAP = _map(
    "slide1",
    view={
        "type": "presentation",
        "width": 1920,
        "height": 1080,
        "theme": "midnight",
        "elements": [
            _element(
                "shape",
                "s1",
                shape="rect",
                stroke_width=1,
                corner_radius=0,
                dash="solid",
                fill="#3b82f6",
            ),
            _element(
                "text",
                "t1",
                text="Title",
                font_size=16,
                font_weight="normal",
                font_style="normal",
                text_align="left",
                line_height=1.3,
                letter_spacing=0,
            ),
        ],
    },
)


def test_create_show_list_delete(clients: ClientRegistry) -> None:
    created = clients.Maps.create(config=_STATIC_MAP)
    assert created.json["extensions"]["config"]["name"] == "map1"

    shown = clients.Maps.get("map1")
    assert shown.json["extensions"]["config"]["alias"] == "Map One"
    assert shown.json["extensions"]["can_edit"] is True
    # The show response carries the GUI signature the SPA relays to the daemon.
    assert shown.json["extensions"]["config_b64"]
    assert shown.json["extensions"]["sig"]

    listed = clients.Maps.get_all()
    assert any(entry["id"] == "map1" for entry in listed.json["value"])

    clients.Maps.delete("map1", etag="valid_etag")
    clients.Maps.get("map1", expect_ok=False).assert_status_code(404)


def test_create_duplicate_returns_409(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_STATIC_MAP)
    clients.Maps.create(config=_STATIC_MAP, expect_ok=False).assert_status_code(409)


def test_update_roundtrip_with_valid_etag(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_STATIC_MAP)
    updated = {**_STATIC_MAP, "alias": "Renamed"}
    resp = clients.Maps.edit("map1", config=updated, etag="valid_etag")
    assert resp.json["extensions"]["config"]["alias"] == "Renamed"
    assert clients.Maps.get("map1").json["extensions"]["config"]["alias"] == "Renamed"


def test_update_with_stale_etag_returns_412(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_STATIC_MAP)
    clients.Maps.edit(
        "map1", config=_STATIC_MAP, etag="invalid_etag", expect_ok=False
    ).assert_status_code(412)


def test_update_missing_returns_404(clients: ClientRegistry) -> None:
    clients.Maps.edit(
        "does-not-exist", config=_map("does-not-exist"), etag="star", expect_ok=False
    ).assert_status_code(404)


def test_delete_missing_returns_404(clients: ClientRegistry) -> None:
    clients.Maps.delete("does-not-exist", expect_ok=False).assert_status_code(404)


def test_presentation_map_discriminated_union_roundtrips(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_PRESENTATION_MAP)
    elements = clients.Maps.get("slide1").json["extensions"]["config"]["view"]["elements"]
    assert {el["kind"] for el in elements} == {"shape", "text"}


def test_show_map_with_unrepresentable_stored_spec_returns_clean_409(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A stored spec that no longer fits the model must answer 409, not crash with
    # an unhandled 500 (the list tolerates the same shape via ``utils._list_view``).
    clients.Maps.create(config=_STATIC_MAP)

    def _raise_validation_error(_spec: object) -> object:
        return utils._MAP_ADAPTER.validate_python({"name": "broken"})  # noqa: SLF001

    monkeypatch.setattr(utils, "map_from_spec", _raise_validation_error)
    resp = clients.Maps.get("map1", expect_ok=False)
    resp.assert_status_code(409)
    assert "cannot be represented" in resp.json["title"]


def test_new_map_is_private_by_default(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_STATIC_MAP)
    assert clients.Maps.get("map1").json["extensions"]["visibility"]["publish"] == "private"


def test_new_map_is_in_the_monitor_menu_by_default(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_STATIC_MAP)
    visibility = clients.Maps.get("map1").json["extensions"]["visibility"]
    assert visibility["hide_in_monitor_menu"] is False


def test_map_created_out_of_the_monitor_menu_is_listed_as_such(clients: ClientRegistry) -> None:
    clients.Maps.create(
        config=_STATIC_MAP, visibility={"publish": "private", "hide_in_monitor_menu": True}
    )

    assert clients.Maps.get("map1").json["extensions"]["visibility"]["hide_in_monitor_menu"]
    listed = {entry["id"]: entry for entry in clients.Maps.get_all().json["value"]}
    assert listed["map1"]["extensions"]["visibility"]["hide_in_monitor_menu"] is True


def test_update_keeps_the_menu_choice_unless_the_visibility_is_sent(
    clients: ClientRegistry,
) -> None:
    clients.Maps.create(
        config=_STATIC_MAP, visibility={"publish": "private", "hide_in_monitor_menu": True}
    )

    kept = clients.Maps.edit("map1", config={**_STATIC_MAP, "alias": "Renamed"})
    assert kept.json["extensions"]["visibility"]["hide_in_monitor_menu"] is True

    shown = clients.Maps.edit(
        "map1", config=_STATIC_MAP, visibility={"publish": "private", "hide_in_monitor_menu": False}
    )
    assert shown.json["extensions"]["visibility"]["hide_in_monitor_menu"] is False


@pytest.mark.parametrize(
    "name",
    ["all_hosts", "service_problems", "infrastructure", "monitoring_folders", "noc_wall"],
)
def test_builtin_maps_serialize_through_the_rest_model(clients: ClientRegistry, name: str) -> None:
    # The shipped built-ins must be complete maps: showing one round-trips the
    # stored spec through the full REST map model (guards against a built-in
    # that omits a structural field the daemon would otherwise default).
    shown = clients.Maps.get(name)
    assert shown.json["extensions"]["is_builtin"] is True
    assert shown.json["extensions"]["visibility"]["hide_in_monitor_menu"] is True
    assert shown.json["extensions"]["config"]["name"] == name


def test_customizing_a_builtin_creates_an_own_override(clients: ClientRegistry) -> None:
    # A shipped built-in map is customizable in place: the update resolves the
    # built-in by name and writes an own override, so operators can tailor the
    # built-in operator maps.
    shown = clients.Maps.get("all_hosts")
    assert shown.json["extensions"]["is_builtin"] is True

    updated = clients.Maps.edit(
        "all_hosts", config=_map("all_hosts", alias="My Hosts"), etag="star"
    )
    assert updated.json["extensions"]["config"]["alias"] == "My Hosts"
    assert updated.json["extensions"]["is_builtin"] is False
    # The override starts from the built-in's place outside the Monitor menu.
    assert updated.json["extensions"]["visibility"]["hide_in_monitor_menu"] is True

    reread = clients.Maps.get("all_hosts")
    assert reread.json["extensions"]["config"]["alias"] == "My Hosts"
    assert reread.json["extensions"]["is_builtin"] is False


def test_deleting_a_builtin_is_refused(clients: ClientRegistry) -> None:
    assert clients.Maps.get("all_hosts").json["extensions"]["is_builtin"] is True
    clients.Maps.delete("all_hosts", expect_ok=False).assert_status_code(403)


def test_update_with_mismatched_config_name_returns_400(clients: ClientRegistry) -> None:
    # The map to write is the path map; a body naming a different map must be
    # rejected rather than stored under the path key with a divergent payload name
    # (which would also get GUI-signed under that wrong name for the daemon).
    clients.Maps.create(config=_STATIC_MAP)
    clients.Maps.edit("map1", config=_map("map2"), etag="star", expect_ok=False).assert_status_code(
        400
    )


@pytest.mark.parametrize("scope", ["contact_groups", "sites"])
def test_publish_without_targets_returns_400(clients: ClientRegistry, scope: str) -> None:
    # Sharing to groups/sites with no targets would clamp silently to private;
    # it must be an explicit 400 instead.
    clients.Maps.create(
        config=_STATIC_MAP,
        visibility={"publish": scope, "hide_in_monitor_menu": False},
        expect_ok=False,
    ).assert_status_code(400)
    clients.Maps.create(
        config=_STATIC_MAP,
        visibility={"publish": scope, "groups": [], "hide_in_monitor_menu": False},
        expect_ok=False,
    ).assert_status_code(400)


def test_object_rejects_null_for_non_nullable_line_fields(clients: ClientRegistry) -> None:
    # ``line_perfdata_label``/``line_weather_color`` are non-nullable in the daemon
    # map schema; the REST mirror must not advertise them as nullable (an explicit
    # ``null`` would be stored and then rejected by the daemon on register).
    map_spec = _map(
        "map1",
        objects=[_host_object("o1", obj_type="line", line={"perfdata_label": None})],
    )
    clients.Maps.create(config=map_spec, expect_ok=False).assert_status_code(400)


# Pagetype permission model (own / foreign-in-place / built-in override) across
# the CRUD endpoints, exercised with distinct built-in roles:
#   * admin -> edit/delete own *and* foreign maps
#   * user  -> edit/delete own only (no edit_foreign_map / delete_foreign_map)
#   * guest -> view only (no edit_map)
# The default ``clients`` are authenticated as ``with_automation_user`` (admin); the
# helper below runs a block as another user and restores the admin afterwards.


@contextmanager
def _acting_as(
    clients: ClientRegistry,
    user: tuple[UserId, str],
    admin: tuple[UserId, str],
) -> Iterator[None]:
    clients.Maps.set_credentials(str(user[0]), user[1])
    try:
        yield
    finally:
        clients.Maps.set_credentials(str(admin[0]), admin[1])


@pytest.fixture(name="map_owned_by_user")
def fixture_map_owned_by_user(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    with_automation_user_not_admin: tuple[UserId, str],
) -> str:
    """A published map owned by a non-admin user — foreign from the admin's POV."""
    with _acting_as(clients, with_automation_user_not_admin, with_automation_user):
        clients.Maps.create(
            config=_map("umap"), visibility={"publish": "all", "hide_in_monitor_menu": False}
        )
    return "umap"


@pytest.fixture(name="admin_shared_map")
def fixture_admin_shared_map(clients: ClientRegistry) -> str:
    """A published map owned by the admin — foreign from a normal user's POV."""
    clients.Maps.create(
        config=_map("shared"), visibility={"publish": "all", "hide_in_monitor_menu": False}
    )
    return "shared"


def test_show_foreign_map_declares_delete_foreign_permission(
    clients: ClientRegistry,
    map_owned_by_user: str,
    with_automation_user_not_admin: tuple[UserId, str],
) -> None:
    # Serializing a foreign, non-built-in map runs ``MapPage.may_delete``, which
    # checks ``general.delete_foreign_map``. That permission must be declared on the
    # endpoint or the framework's permission tracker raises the moment a non-owner is
    # involved. The admin holds it, so ``can_delete`` is True.
    shown = clients.Maps.get(map_owned_by_user)
    assert shown.json["extensions"]["owner"] == str(with_automation_user_not_admin[0])
    assert shown.json["extensions"]["is_builtin"] is False
    assert shown.json["extensions"]["can_edit"] is True
    assert shown.json["extensions"]["can_delete"] is True


def test_list_includes_foreign_map(clients: ClientRegistry, map_owned_by_user: str) -> None:
    # Listing serializes every visible map, foreign ones included — same
    # ``may_delete`` permission check as show, across the whole collection.
    listed = clients.Maps.get_all()
    assert any(entry["id"] == map_owned_by_user for entry in listed.json["value"])


def test_admin_edits_foreign_map_in_place(
    clients: ClientRegistry,
    map_owned_by_user: str,
    with_automation_user_not_admin: tuple[UserId, str],
) -> None:
    # Editing a foreign map writes it back under its original owner (no fork to the
    # editor) — the same in-place behavior the GUI save uses.
    updated = clients.Maps.edit(map_owned_by_user, config=_map("umap", alias="Edited"), etag="star")
    assert updated.json["extensions"]["config"]["alias"] == "Edited"
    assert updated.json["extensions"]["owner"] == str(with_automation_user_not_admin[0])


def test_admin_deletes_foreign_map(clients: ClientRegistry, map_owned_by_user: str) -> None:
    clients.Maps.delete(map_owned_by_user, etag="star")
    clients.Maps.get(map_owned_by_user, expect_ok=False).assert_status_code(404)


def test_normal_user_may_view_but_not_edit_or_delete_foreign_map(
    clients: ClientRegistry,
    admin_shared_map: str,
    with_automation_user: tuple[UserId, str],
    with_automation_user_not_admin: tuple[UserId, str],
) -> None:
    with _acting_as(clients, with_automation_user_not_admin, with_automation_user):
        shown = clients.Maps.get(admin_shared_map)
        # A published map is visible, but a normal user owns neither the edit-foreign
        # nor the delete-foreign permission.
        assert shown.json["extensions"]["can_edit"] is False
        assert shown.json["extensions"]["can_delete"] is False
        clients.Maps.edit(
            admin_shared_map, config=_map("shared", alias="X"), etag="star", expect_ok=False
        ).assert_status_code(403)
        clients.Maps.delete(admin_shared_map, etag="star", expect_ok=False).assert_status_code(403)


def test_guest_may_not_create_map(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    with_automation_user_guest: tuple[UserId, str],
) -> None:
    # ``maps.use`` grants viewing; creating still needs the pagetype edit grant
    # (``general.edit_map``), which the guest role lacks.
    with _acting_as(clients, with_automation_user_guest, with_automation_user):
        clients.Maps.create(config=_map("g1"), expect_ok=False).assert_status_code(403)


def test_authoring_settings_are_served_to_the_spa(clients: ClientRegistry) -> None:
    # The editor's defaults are GUI-owned globals; the SPA fetches them here
    # rather than receiving them as page props, so this endpoint is on its boot
    # path and its absence would leave the editor without defaults.
    read = clients.Maps.get_authoring_settings().json
    settings = read["settings"]
    # Spot-check across the two FormSpec globals this flattens: object appearance
    # from one, new-map defaults from the other.
    assert settings["icon_size"] == 30
    assert settings["label_show"] is True
    assert settings["default_map_type"] == "static"
    assert settings["default_render_mode"] == "default"
    # Site-aware: resolved from the local site's seeded connection, not a constant.
    assert settings["default_backend_id"].startswith("cmk_")
    # The geo maps' tile source rides along: the SPA draws no tiles of its own
    # choosing, and the page policy allows exactly what is named here.
    assert read["tiles"]["default_url"] == "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    assert "https://tile.openstreetmap.org/" in read["tiles"]["allowed_sources"]
