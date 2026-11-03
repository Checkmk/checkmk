#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, ExitStack
from pathlib import Path

import pytest

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.logged_in import save_user_file
from cmk.gui.userdb import UserRolesConfigFile
from cmk.maps import gui as maps_gui
from cmk.maps.gui.legacy_maps import legacy_maps_dir
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.store import get_own_map
from cmk.maps.rest_api.utils import map_from_spec
from cmk.update_config.internal import ExpiryVersion
from cmk.update_config.plugins.actions.maps import MigrateLegacyMaps
from cmk.utils import paths
from tests.testlib.unit.gui.users import create_and_destroy_user

_LOGGER = logging.getLogger("test-maps-migration")

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4"/></svg>'
# The icons Maps ships; OrbVis shipped the same set under the same names.
_BUILTIN_ICONS = Path(maps_gui.__file__).parent / "builtin_icons"


@pytest.fixture(name="admin")
def fixture_admin(with_admin: tuple[UserId, str]) -> UserId:
    return with_admin[0]


def _complete_map(**overrides: object) -> dict[str, object]:
    """A representative board payload with the common fields an operator sets."""
    map_spec: dict[str, object] = {
        "alias": "Legacy",
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


def _complete_object(**overrides: object) -> dict[str, object]:
    """A board object with the geometry fields the strict REST model requires."""
    obj: dict[str, object] = {"id": "o1", "type": "host", "x": 10, "y": 20, "url_target": "_blank"}
    obj.update(overrides)
    return obj


def _presentation_view(**overrides: object) -> dict[str, object]:
    view: dict[str, object] = {
        "type": "presentation",
        "width": 1920,
        "height": 1080,
        "theme": "midnight",
        "elements": [],
    }
    view.update(overrides)
    return view


def _view(spec: Mapping[str, object]) -> dict[str, object]:
    view = spec["view"]
    assert isinstance(view, dict)
    return view


def _objects(spec: Mapping[str, object]) -> list[dict[str, object]]:
    """Narrow the stored spec's ``objects`` entries so assertions can index them."""
    objects = spec["objects"]
    assert isinstance(objects, list)
    for obj in objects:
        assert isinstance(obj, dict)
    return objects


def _action() -> MigrateLegacyMaps:
    return MigrateLegacyMaps(
        name="migrate_legacy_maps",
        title="test",
        sort_index=0,
        expiry_version=ExpiryVersion.NEVER,
    )


def _write_board(name: str, map_spec: dict[str, object]) -> Path:
    boards_dir = legacy_maps_dir() / "boards"
    boards_dir.mkdir(parents=True, exist_ok=True)
    path = boards_dir / f"{name}.json"
    path.write_text(json.dumps(map_spec))
    return path


def _write_connections(*entries: dict[str, object]) -> None:
    _write_legacy_file("connections.json", json.dumps(list(entries)).encode())


_REMOTE_CONNECTION = {"id": "live_2", "type": "livestatus", "host": "remote.example", "port": 6557}


def _write_legacy_file(relative: str, contents: bytes) -> None:
    path = legacy_maps_dir() / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)


def _maps_images_dir() -> Path:
    return paths.omd_root / "var" / "maps" / "images"


def _write_maps_icon(name: str, contents: bytes) -> None:
    _maps_images_dir().mkdir(parents=True, exist_ok=True)
    (_maps_images_dir() / name).write_bytes(contents)


def _maps_backgrounds_dir() -> Path:
    return paths.omd_root / "var" / "maps" / "backgrounds"


def _run_with_board(name: str, map_spec: dict[str, object]) -> None:
    _write_board(name, map_spec)
    _action()(_LOGGER)


def _migrated(admin: UserId, name: str, map_spec: dict[str, object]) -> MapPage:
    _run_with_board(name, map_spec)
    page = get_own_map(admin, name)
    assert page is not None
    return page


def _owners_of(name: str) -> list[UserId]:
    return [owner for owner, stored in MapPage.load_raw() if stored == name]


def _record_path() -> Path:
    return paths.omd_root / "var" / "maps" / "legacy_maps_migration.mk"


def _record() -> Mapping[str, Mapping[str, str]]:
    record: Mapping[str, Mapping[str, str]] = store.load_object_from_file(
        _record_path(), default={}
    )
    return record


def _outcomes() -> Mapping[str, str]:
    return _record().get("boards", {})


def _copied_icons() -> Mapping[str, str]:
    return _record().get("icons", {})


def _role_permissions(role_id: str) -> Mapping[str, bool]:
    return UserRolesConfigFile().load_for_reading()[role_id]["permissions"]


def _set_role_permissions(role_id: str, permissions: Mapping[str, bool]) -> None:
    roles_file = UserRolesConfigFile()
    roles = roles_file.load_for_modification()
    roles[role_id]["permissions"].update(permissions)
    roles_file.save(roles, pprint_value=False)


_NOT_ROOT = pytest.mark.skipif(os.getuid() == 0, reason="root reads and writes through file modes")


@contextmanager
def _unreadable(path: Path) -> Iterator[None]:
    path.chmod(0o000)
    try:
        yield
    finally:
        path.chmod(0o600)


@contextmanager
def _read_only_profile(user_id: UserId) -> Iterator[None]:
    profile = paths.profile_dir / user_id
    profile.chmod(0o500)
    try:
        yield
    finally:
        profile.chmod(0o770)


def _run_with_failing_store(admin: UserId) -> None:
    # An existing store file: the store lock opens it, only writing it fails.
    save_user_file("user_maps", {}, admin)
    with _read_only_profile(admin), pytest.raises(MKGeneralException):
        _action()(_LOGGER)


# --- what a board becomes ---------------------------------------------------


def test_board_becomes_a_published_map_of_the_admin(admin: UserId) -> None:
    page = _migrated(admin, "legacy1", _complete_map())

    # Published, as an OrbVis board was not owned by anyone.
    assert page.config.public is True


def test_board_keeps_its_alias(admin: UserId) -> None:
    page = _migrated(admin, "legacy1", _complete_map(alias="Legacy One"))

    assert page.config.map_spec["alias"] == "Legacy One"


def test_stored_map_passes_the_rest_model(admin: UserId) -> None:
    page = _migrated(admin, "legacy1", _complete_map())

    map_from_spec(page.config.map_spec)


@pytest.mark.usefixtures("with_admin")
def test_the_legacy_map_file_is_left_alone() -> None:
    # OrbVis may still be installed and keeps reading its boards.
    path = _write_board("legacy1", _complete_map())
    before = path.read_text()

    _action()(_LOGGER)

    assert path.read_text() == before


def test_legacy_backend_id_becomes_the_connection(admin: UserId) -> None:
    _write_connections(_REMOTE_CONNECTION)
    map_spec = _complete_map(backend_id="live_2")
    del map_spec["connection_id"]

    spec = _migrated(admin, "legacy", map_spec).config.map_spec

    assert spec["connection_id"] == "live_2"
    assert "backend_id" not in spec


def test_a_connection_to_the_site_livestatus_becomes_the_site_connection(admin: UserId) -> None:
    _write_connections(
        {"id": "live_1", "type": "livestatus", "socket_path": str(paths.livestatus_unix_socket)}
    )
    map_spec = _complete_map(objects=[_complete_object(connection_id="live_1")])

    spec = _migrated(admin, "local", map_spec).config.map_spec

    assert spec["connection_id"] == f"cmk_{omd_site()}"
    assert _objects(spec)[0]["connection_id"] == f"cmk_{omd_site()}"


def test_the_site_livestatus_behind_a_symlink_becomes_the_site_connection(
    admin: UserId, tmp_path: Path
) -> None:
    paths.livestatus_unix_socket.parent.mkdir(parents=True, exist_ok=True)
    (link := tmp_path / "run").symlink_to(paths.livestatus_unix_socket.parent)
    _write_connections({"id": "live_1", "type": "livestatus", "socket_path": str(link / "live")})

    spec = _migrated(admin, "linked", _complete_map(connection_id="live_1")).config.map_spec

    assert spec["connection_id"] == f"cmk_{omd_site()}"


def test_an_unknown_connection_becomes_the_site_connection(admin: UserId) -> None:
    spec = _migrated(admin, "unknown", _complete_map(connection_id="test")).config.map_spec

    assert spec["connection_id"] == f"cmk_{omd_site()}"


def test_a_connection_elsewhere_keeps_its_id(admin: UserId) -> None:
    _write_connections(_REMOTE_CONNECTION)
    map_spec = _complete_map(
        connection_id="live_2", objects=[_complete_object(connection_id="live_2")]
    )

    spec = _migrated(admin, "remote", map_spec).config.map_spec

    assert spec["connection_id"] == "live_2"
    assert _objects(spec)[0]["connection_id"] == "live_2"


def test_a_tcp_connection_with_the_site_socket_keeps_its_id(admin: UserId) -> None:
    _write_connections(
        {
            "id": "live_3",
            "type": "livestatus",
            "host": "remote.example.com",
            "socket_path": str(paths.livestatus_unix_socket),
        }
    )

    spec = _migrated(admin, "tcp", _complete_map(connection_id="live_3")).config.map_spec

    assert spec["connection_id"] == "live_3"


def test_the_keys_the_pagetype_holds_are_not_kept_in_the_map(admin: UserId) -> None:
    spec = _migrated(
        admin, "legacy", _complete_map(show_in_lists=False, readonly=False)
    ).config.map_spec

    assert "show_in_lists" not in spec
    assert "readonly" not in spec


@pytest.mark.parametrize(("shown", "hidden"), [(True, False), (False, True), (None, False)])
def test_legacy_show_in_lists_becomes_hidden(
    admin: UserId,
    shown: bool | None,
    hidden: bool,
) -> None:
    overrides = {} if shown is None else {"show_in_lists": shown}

    page = _migrated(admin, "legacy", _complete_map(**overrides))

    assert page.config.hidden is hidden


def test_weathermap_line_style_is_split_up(admin: UserId) -> None:
    map_spec = _complete_map(
        objects=[_complete_object(id="l1", type="line", line_style="weathermap")]
    )

    obj = _objects(_migrated(admin, "wm", map_spec).config.map_spec)[0]

    assert obj["line_style"] == "arrow_inward"
    assert obj["line_perfdata_label"] == "bandwidth"
    assert obj["line_weather_color"] is True


_DYNGROUP = {"type": "dyngroup", "object_filter": "Filter: name ~ ^web\n"}


def test_a_geo_bundle_keeps_counting_its_services(admin: UserId) -> None:
    bundle = _complete_object(
        object_types="host", bundle_kind="static", recognize_services=False, **_DYNGROUP
    )

    obj = _objects(_migrated(admin, "bundle", _complete_map(objects=[bundle])).config.map_spec)[0]

    assert obj["recognize_services"] is True


@pytest.mark.parametrize(
    "group",
    [
        pytest.param({"object_types": "host", "recognize_services": False}, id="hosts"),
        pytest.param({"object_types": "service"}, id="services"),
    ],
)
def test_a_dynamic_group_keeps_its_service_counting(
    admin: UserId, group: dict[str, object]
) -> None:
    map_spec = _complete_map(objects=[_complete_object(**_DYNGROUP, **group)])

    obj = _objects(_migrated(admin, "dyn", map_spec).config.map_spec)[0]

    assert obj.get("recognize_services") == group.get("recognize_services")


def test_member_patterns_orbvis_never_applied_are_dropped(admin: UserId) -> None:
    # OrbVis asked for state names; Maps would read them as a pattern on names.
    map_spec = _complete_map(
        objects=[
            _complete_object(
                id="g1",
                type="hostgroup",
                group_name="web",
                exclude_members="test-*",
                exclude_member_states="DOWN,CRITICAL\nOr: 2",
            )
        ]
    )

    obj = _objects(_migrated(admin, "excl", map_spec).config.map_spec)[0]

    assert "exclude_members" not in obj
    assert "exclude_member_states" not in obj


def test_a_single_graph_metric_becomes_a_list(admin: UserId) -> None:
    map_spec = _complete_map(
        objects=[_complete_object(id="g1", type="graph", graph_metric="load1")]
    )

    obj = _objects(_migrated(admin, "graph", map_spec).config.map_spec)[0]

    assert obj["graph_metric"] == ["load1"]


def test_graph_metrics_the_daemon_would_drop_are_dropped(admin: UserId) -> None:
    # The daemon loads these; the REST model would reject them.
    map_spec = _complete_map(
        objects=[
            _complete_object(id="g1", type="graph", graph_metric=["load1", 5, "load5"]),
            _complete_object(id="g2", type="graph", graph_metric=42),
        ]
    )

    objects = _objects(_migrated(admin, "graph2", map_spec).config.map_spec)

    assert objects[0]["graph_metric"] == ["load1", "load5"]
    assert objects[1]["graph_metric"] is None


def test_a_sparse_map_gets_the_daemon_defaults(admin: UserId) -> None:
    spec = _migrated(admin, "sparse", {"view": {"type": "static"}}).config.map_spec

    assert spec["alias"] == ""
    assert spec["connection_id"] == f"cmk_{omd_site()}"
    assert spec["rotation_interval"] == 0
    assert spec["sort_order"] == 0
    assert spec["click_action"] == "link"
    assert spec["objects"] == []


def test_a_sparse_object_gets_the_daemon_defaults(admin: UserId) -> None:
    sparse = {"id": "o1", "type": "host", "host_name": "web-01", "label": {"show": False}}

    obj = _objects(
        _migrated(admin, "sparse-object", _complete_map(objects=[sparse])).config.map_spec
    )[0]

    assert (obj["x"], obj["y"], obj["url_target"]) == (0, 0, "_blank")
    assert obj["label"] == {
        "show": False,
        "x": 0,
        "y": 0,
        "size": 11,
        "color": "#ffffff",
        "background": "transparent",
    }


def test_a_sparse_display_gets_the_daemon_defaults(admin: UserId) -> None:
    sparse = _complete_object(display={"image": "server.svg"})

    obj = _objects(
        _migrated(admin, "sparse-display", _complete_map(objects=[sparse])).config.map_spec
    )[0]

    assert obj["display"] == {"mode": "icon", "image": "server.svg"}


def test_a_sparse_radar_view_gets_the_daemon_defaults(admin: UserId) -> None:
    spec = _migrated(admin, "sparse-radar", _complete_map(view={"type": "radar"})).config.map_spec

    assert (_view(spec)["filter"], _view(spec)["filter_value"]) == ("hostgroup", "")


@pytest.mark.parametrize(
    ("css", "hex_color"),
    [("rgb(0, 0, 0)", "#000000"), ("rgba(255,128,0,0.5)", "#ff800080")],
)
def test_a_css_rgb_color_becomes_hex(
    admin: UserId,
    css: str,
    hex_color: str,
) -> None:
    # OrbVis took rgb() colors over from NagVis maps; the REST model only knows hex.
    label = {"show": True, "x": 0, "y": 0, "size": 11, "color": css, "background": "transparent"}
    map_spec = _complete_map(objects=[_complete_object(label=label)])

    obj = _objects(_migrated(admin, "colors", map_spec).config.map_spec)[0]

    assert isinstance(obj["label"], dict)
    assert obj["label"]["color"] == hex_color


def test_a_geo_view_past_the_limits_is_brought_within_them(admin: UserId) -> None:
    # OrbVis saved Leaflet's view as is: past the antimeridian, up to zoom 19.
    view = {"type": "worldmap", "lat": 48.1, "lng": 191.5, "zoom": 19}

    spec = _migrated(admin, "geo", _complete_map(view=view)).config.map_spec

    assert (_view(spec)["lat"], _view(spec)["lng"], _view(spec)["zoom"]) == (48.1, -168.5, 18)


@pytest.mark.parametrize(
    ("broken", "expected"),
    [
        ({"zoom": float("inf")}, (48.1, 11.5, 5)),
        ({"lng": float("nan")}, (48.1, 10.0, 7)),
        ({"lat": "48.1"}, (51.0, 11.5, 7)),
    ],
)
def test_a_geo_view_value_that_is_no_number_gets_the_default(
    admin: UserId, broken: dict[str, object], expected: tuple[float, float, int]
) -> None:
    view = {"type": "worldmap", "lat": 48.1, "lng": 11.5, "zoom": 7, **broken}

    spec = _migrated(admin, "geo", _complete_map(view=view)).config.map_spec

    assert (_view(spec)["lat"], _view(spec)["lng"], _view(spec)["zoom"]) == expected


def test_a_geo_object_without_label_settings_stays_captioned(admin: UserId) -> None:
    # OrbVis captioned such an object on a geo board, not on a static one.
    view = {"type": "worldmap", "lat": 51.0, "lng": 10.0, "zoom": 5}
    map_spec = _complete_map(view=view, objects=[_complete_object()])

    obj = _objects(_migrated(admin, "geo-label", map_spec).config.map_spec)[0]

    assert isinstance(obj["label"], dict)
    assert obj["label"]["show"] is True


def test_a_static_object_without_label_settings_stays_uncaptioned(admin: UserId) -> None:
    map_spec = _complete_map(objects=[_complete_object()])

    obj = _objects(_migrated(admin, "static-label", map_spec).config.map_spec)[0]

    assert obj.get("label") is None


# --- images -----------------------------------------------------------------


def test_the_icon_library_is_copied(admin: UserId) -> None:
    _write_legacy_file("images/rack.png", _PNG)

    _migrated(admin, "legacy", _complete_map())

    assert (_maps_images_dir() / "rack.png").read_bytes() == _PNG


@pytest.mark.usefixtures("with_admin")
def test_demo_boards_alone_bring_in_no_icons() -> None:
    _write_legacy_file("images/rack.png", _PNG)
    _run_with_board("demo-static", _complete_map(readonly=True))

    assert not (_maps_images_dir() / "rack.png").exists()


@pytest.mark.usefixtures("with_admin")
def test_a_board_that_fails_alone_brings_in_no_icons() -> None:
    _write_legacy_file("images/rack.png", _PNG)
    _run_with_board("broken", _complete_map(view={"type": "not-a-real-view"}))

    assert not (_maps_images_dir() / "rack.png").exists()


def test_an_icon_that_is_no_image_is_not_copied(admin: UserId) -> None:
    _write_legacy_file("images/fake.png", b"not an image")

    _migrated(admin, "legacy", _complete_map())

    assert not (_maps_images_dir() / "fake.png").exists()


def test_an_icon_of_an_unsupported_type_is_reported(
    admin: UserId, caplog: pytest.LogCaptureFixture
) -> None:
    _write_legacy_file("images/router.gif", b"GIF89a")

    _migrated(admin, "legacy", _complete_map())

    assert not (_maps_images_dir() / "router.gif").exists()
    assert "router.gif" in caplog.text


def test_a_different_icon_of_the_same_name_is_not_replaced(admin: UserId) -> None:
    _write_maps_icon("rack.png", _PNG + b"maps")
    _write_legacy_file("images/rack.png", _PNG)

    _migrated(admin, "legacy", _complete_map())

    assert (_maps_images_dir() / "rack.png").read_bytes() == _PNG + b"maps"


def test_a_board_follows_its_icon_to_the_new_name(admin: UserId) -> None:
    _write_maps_icon("rack.png", _PNG + b"maps")
    _write_legacy_file("images/rack.png", _PNG)
    map_spec = _complete_map(objects=[_complete_object(image_src="rack.png")])

    obj = _objects(_migrated(admin, "legacy", map_spec).config.map_spec)[0]

    assert obj["image_src"] == "rack-2.png"
    assert (_maps_images_dir() / "rack-2.png").read_bytes() == _PNG


def test_an_icon_name_is_cleaned_like_an_upload(admin: UserId) -> None:
    # Uploads before OrbVis cleaned names may carry "#" or "?", which break the URL.
    _write_legacy_file("images/rack #1.PNG", _PNG)
    map_spec = _complete_map(objects=[_complete_object(image_src="rack #1.PNG")])

    obj = _objects(_migrated(admin, "legacy", map_spec).config.map_spec)[0]

    assert obj["image_src"] == "rack__1.png"
    assert (_maps_images_dir() / "rack__1.png").read_bytes() == _PNG


def test_a_board_valid_only_with_its_icon_cleaned_is_migrated(admin: UserId) -> None:
    # "rack:1.png" reads as a URL scheme, which a slide's image fields refuse; the
    # board is checked before the copy, so the check has to see the cleaned name.
    _write_legacy_file("images/rack:1.png", _PNG)
    view = _presentation_view(background_image="rack:1.png")

    spec = _migrated(admin, "legacy", _complete_map(view=view)).config.map_spec

    assert _view(spec)["background_image"] == "rack_1.png"
    assert (_maps_images_dir() / "rack_1.png").read_bytes() == _PNG


def test_an_unclean_icon_that_is_not_copied_does_not_fail_the_board(admin: UserId) -> None:
    # The copy leaves the icon out, but the board must still see the cleaned name,
    # or it fails after the copy on every update.
    _write_legacy_file("images/logo:1.png", b"not an image")
    view = _presentation_view(background_image="logo:1.png")

    spec = _migrated(admin, "legacy", _complete_map(view=view)).config.map_spec

    assert _view(spec)["background_image"] == "logo_1.png"


def test_a_data_element_follows_its_icon_to_the_new_name(admin: UserId) -> None:
    _write_maps_icon("rack.png", _PNG + b"maps")
    _write_legacy_file("images/rack.png", _PNG)
    # Stored flat, as the REST model's ``transform`` is only nested on the wire.
    element = {
        "kind": "data",
        "id": "d1",
        "x": 0,
        "y": 0,
        "w": 100,
        "h": 100,
        "rotation": 0,
        "z": 0,
        "opacity": 1,
        "locked": False,
        "hidden": False,
        "only_hard_states": False,
        "display": {"mode": "icon", "image": "rack.png"},
    }
    view = _presentation_view(elements=[element])

    spec = _migrated(admin, "legacy", _complete_map(view=view)).config.map_spec

    elements = _view(spec)["elements"]
    assert isinstance(elements, list)
    assert elements[0]["display"]["image"] == "rack-2.png"


def test_an_own_icon_under_a_builtin_name_keeps_its_image(admin: UserId) -> None:
    # Before OrbVis protected built-ins, an upload could replace one; server-2.svg is
    # a built-in too, so the icon moves on to server-3.svg.
    _write_legacy_file("images/server.svg", _SVG)
    map_spec = _complete_map(objects=[_complete_object(image_src="server.svg")])

    obj = _objects(_migrated(admin, "legacy", map_spec).config.map_spec)[0]

    assert obj["image_src"] == "server-3.svg"
    assert (_maps_images_dir() / "server-3.svg").read_bytes() == _SVG


def test_a_builtin_icon_stays_the_builtin(admin: UserId) -> None:
    _write_legacy_file("images/server.svg", (_BUILTIN_ICONS / "server.svg").read_bytes())
    map_spec = _complete_map(objects=[_complete_object(image_src="server.svg")])

    obj = _objects(_migrated(admin, "legacy", map_spec).config.map_spec)[0]

    assert obj["image_src"] == "server.svg"


def test_the_copied_icons_are_recorded(admin: UserId) -> None:
    _write_maps_icon("rack.png", _PNG + b"maps")
    _write_legacy_file("images/rack.png", _PNG)
    _write_legacy_file("images/switch.png", _PNG)
    _write_legacy_file("images/fake.png", b"not an image")

    _migrated(admin, "legacy", _complete_map())

    assert _copied_icons() == {"rack.png": "rack-2.png", "switch.png": "switch.png"}


def test_an_icon_deleted_after_the_migration_is_not_copied_again(admin: UserId) -> None:
    _write_legacy_file("images/rack.png", _PNG)
    _run_with_board("first", _complete_map())
    (_maps_images_dir() / "rack.png").unlink()

    _migrated(admin, "later", _complete_map(objects=[_complete_object(image_src="rack.png")]))

    assert not (_maps_images_dir() / "rack.png").exists()


def test_a_later_board_refers_to_the_name_its_icon_was_copied_under(admin: UserId) -> None:
    # Maps' own rack.png pushed OrbVis's to rack-2.png; deleting it afterwards must
    # not make a later board bring OrbVis's back under the freed name.
    _write_maps_icon("rack.png", _PNG + b"maps")
    _write_legacy_file("images/rack.png", _PNG)
    _run_with_board("first", _complete_map())
    (_maps_images_dir() / "rack.png").unlink()
    map_spec = _complete_map(objects=[_complete_object(image_src="rack.png")])

    obj = _objects(_migrated(admin, "later", map_spec).config.map_spec)[0]

    assert obj["image_src"] == "rack-2.png"
    assert not (_maps_images_dir() / "rack.png").exists()


def test_a_replaced_icon_is_not_copied_again(admin: UserId) -> None:
    _write_legacy_file("images/rack.png", _PNG)
    _run_with_board("first", _complete_map())
    _write_maps_icon("rack.png", _PNG + b"maps")
    map_spec = _complete_map(objects=[_complete_object(image_src="rack.png")])

    obj = _objects(_migrated(admin, "later", map_spec).config.map_spec)[0]

    assert obj["image_src"] == "rack.png"
    assert (_maps_images_dir() / "rack.png").read_bytes() == _PNG + b"maps"
    assert not (_maps_images_dir() / "rack-2.png").exists()


def test_an_icon_added_to_orbvis_later_is_copied(admin: UserId) -> None:
    _write_legacy_file("images/rack.png", _PNG)
    _run_with_board("first", _complete_map())
    _write_legacy_file("images/switch.png", _PNG)

    _migrated(admin, "later", _complete_map())

    assert (_maps_images_dir() / "switch.png").read_bytes() == _PNG


def test_an_icon_fixed_after_a_failed_copy_is_copied_by_a_later_run(admin: UserId) -> None:
    _write_legacy_file("images/rack.png", b"not an image")
    _run_with_board("first", _complete_map())
    _write_legacy_file("images/rack.png", _PNG)

    _migrated(admin, "later", _complete_map())

    assert (_maps_images_dir() / "rack.png").read_bytes() == _PNG


@_NOT_ROOT
def test_an_icon_that_could_not_be_read_is_copied_by_a_later_run(admin: UserId) -> None:
    _write_legacy_file("images/locked.png", _PNG)
    locked = legacy_maps_dir() / "images" / "locked.png"
    with _unreadable(locked):
        _run_with_board("first", _complete_map())

    _migrated(admin, "later", _complete_map())

    assert (_maps_images_dir() / "locked.png").read_bytes() == _PNG


@_NOT_ROOT
@pytest.mark.usefixtures("with_admin")
def test_an_unreadable_icon_does_not_stop_the_boards() -> None:
    _write_legacy_file("images/locked.png", _PNG)
    locked = legacy_maps_dir() / "images" / "locked.png"
    with _unreadable(locked):
        _run_with_board("legacy", _complete_map())

    assert _outcomes()["legacy"] == "migrated"


@_NOT_ROOT
@pytest.mark.usefixtures("with_admin")
def test_an_unreadable_background_does_not_stop_the_board() -> None:
    _write_legacy_file("boards/backgrounds/floor.png", _PNG)
    locked = legacy_maps_dir() / "boards" / "backgrounds" / "floor.png"
    with _unreadable(locked):
        _run_with_board("legacy", _complete_map(background_image="floor.png"))

    assert _outcomes()["legacy"] == "migrated"


def test_the_background_becomes_the_maps_background(admin: UserId) -> None:
    _write_legacy_file("boards/backgrounds/floor.png", _PNG)

    spec = _migrated(admin, "legacy", _complete_map(background_image="floor.png")).config.map_spec

    stored = spec["background_image"]
    assert isinstance(stored, str)
    assert (_maps_backgrounds_dir() / stored).read_bytes() == _PNG


def test_a_board_background_keeps_covering_the_box_its_objects_are_placed_in(
    admin: UserId,
) -> None:
    spec = _migrated(admin, "legacy", _complete_map(background_image="gone.png")).config.map_spec

    assert spec["background_style"] == "stretch"


def test_a_missing_background_keeps_its_reference(admin: UserId) -> None:
    spec = _migrated(admin, "legacy", _complete_map(background_image="gone.png")).config.map_spec

    assert spec["background_image"] == "gone.png"


# --- who sees the maps ------------------------------------------------------


def test_guest_does_not_see_a_map_it_could_not_see_before(admin: UserId) -> None:
    # OrbVis granted its view permissions to admin and user only.
    _migrated(admin, "legacy", _complete_map())

    assert _role_permissions("guest")["map.legacy"] is False


def test_roles_that_saw_the_board_keep_the_default(admin: UserId) -> None:
    _migrated(admin, "legacy", _complete_map())

    assert "map.legacy" not in _role_permissions("user")
    assert "map.legacy" not in _role_permissions("admin")


def test_a_stale_entry_does_not_hide_a_map_the_role_saw(admin: UserId) -> None:
    _set_role_permissions("user", {"map.legacy": False})

    _migrated(admin, "legacy", _complete_map())

    assert "map.legacy" not in _role_permissions("user")


@pytest.mark.usefixtures("with_admin")
def test_a_board_withheld_from_a_role_stays_withheld() -> None:
    # Without ``view_all`` a role still sees every board whose own view permission
    # it keeps (granted to user by default); a board it was denied stays hidden.
    _set_role_permissions("user", {"orbvis.view_all": False, "orbvis.view_withheld": False})
    _write_board("shown", _complete_map())
    _write_board("withheld", _complete_map())
    _action()(_LOGGER)

    assert "map.shown" not in _role_permissions("user")
    assert _role_permissions("user")["map.withheld"] is False


def test_a_role_without_the_use_permission_sees_no_map(admin: UserId) -> None:
    _set_role_permissions("user", {"orbvis.use": False})

    _migrated(admin, "legacy", _complete_map())

    assert _role_permissions("user")["map.legacy"] is False


# --- who gets the maps ------------------------------------------------------


def test_the_lowest_sorted_admin_gets_the_maps(load_config: Config) -> None:
    with ExitStack() as users:
        for username, role in (("zoe", "admin"), ("amy", "user"), ("bob", "admin")):
            users.enter_context(
                create_and_destroy_user(username=username, role=role, config=load_config)
            )
        _run_with_board("legacy", _complete_map())

        assert _owners_of("legacy") == [UserId("bob")]


def test_cmkadmin_gets_the_maps_before_a_lower_sorted_admin(load_config: Config) -> None:
    with ExitStack() as users:
        for username in ("bob", "cmkadmin"):
            users.enter_context(
                create_and_destroy_user(username=username, role="admin", config=load_config)
            )
        _run_with_board("legacy", _complete_map())

        assert _owners_of("legacy") == [UserId("cmkadmin")]


def test_a_locked_cmkadmin_gets_the_maps(load_config: Config) -> None:
    with ExitStack() as users:
        users.enter_context(
            create_and_destroy_user(
                username="cmkadmin", role="admin", custom_attrs={"locked": True}, config=load_config
            )
        )
        users.enter_context(
            create_and_destroy_user(username="bob", role="admin", config=load_config)
        )
        _run_with_board("legacy", _complete_map())

        assert _owners_of("legacy") == [UserId("cmkadmin")]


@pytest.mark.parametrize(
    "role, automation",
    [
        pytest.param("user", False, id="not-an-admin"),
        pytest.param("admin", True, id="automation"),
    ],
)
def test_a_cmkadmin_that_is_no_human_admin_does_not_get_the_maps(
    load_config: Config, role: str, automation: bool
) -> None:
    with ExitStack() as users:
        users.enter_context(
            create_and_destroy_user(
                username="cmkadmin", role=role, automation=automation, config=load_config
            )
        )
        users.enter_context(
            create_and_destroy_user(username="zoe", role="admin", config=load_config)
        )
        _run_with_board("legacy", _complete_map())

        assert _owners_of("legacy") == [UserId("zoe")]


def test_maps_of_another_admin_than_cmkadmin_are_reported(
    load_config: Config, caplog: pytest.LogCaptureFixture
) -> None:
    with create_and_destroy_user(username="bob", role="admin", config=load_config):
        _run_with_board("legacy", _complete_map())

        assert "Deleting bob removes these maps" in caplog.text


def test_an_automation_admin_does_not_get_the_maps(load_config: Config) -> None:
    # "auto" sorts before "human" but is an automation account; the maps should be
    # owned by a real operator.
    with ExitStack() as users:
        users.enter_context(
            create_and_destroy_user(
                username="auto", role="admin", automation=True, config=load_config
            )
        )
        users.enter_context(
            create_and_destroy_user(username="human", role="admin", config=load_config)
        )
        _run_with_board("legacy", _complete_map())

        assert _owners_of("legacy") == [UserId("human")]


def test_a_locked_admin_does_not_get_the_maps(load_config: Config) -> None:
    # A locked account is likely deleted later, and its maps with it.
    with ExitStack() as users:
        users.enter_context(
            create_and_destroy_user(
                username="amy", role="admin", custom_attrs={"locked": True}, config=load_config
            )
        )
        users.enter_context(
            create_and_destroy_user(username="bob", role="admin", config=load_config)
        )
        _run_with_board("legacy", _complete_map())

        assert _owners_of("legacy") == [UserId("bob")]


def test_a_locked_admin_gets_the_maps_when_no_other_admin_is_left(load_config: Config) -> None:
    with create_and_destroy_user(
        username="amy", role="admin", custom_attrs={"locked": True}, config=load_config
    ):
        _run_with_board("legacy", _complete_map())

        assert _owners_of("legacy") == [UserId("amy")]


def test_without_an_admin_the_boards_wait_for_a_later_run(load_config: Config) -> None:
    with create_and_destroy_user(username="amy", role="user", config=load_config):
        _run_with_board("legacy", _complete_map())

        assert _owners_of("legacy") == []
        assert "legacy" not in _outcomes()


# --- what is recorded -------------------------------------------------------


def test_a_migrated_board_is_recorded(admin: UserId) -> None:
    _migrated(admin, "legacy", _complete_map())

    assert _outcomes()["legacy"] == "migrated"


def test_a_recorded_board_is_not_migrated_again(admin: UserId) -> None:
    _migrated(admin, "legacy", _complete_map(alias="First"))
    _run_with_board("legacy", _complete_map(alias="Changed in OrbVis"))

    page = get_own_map(admin, "legacy")
    assert page is not None
    assert page.config.map_spec["alias"] == "First"


def test_an_invalid_board_is_left_for_a_later_run(admin: UserId) -> None:
    # A board the current schema cannot accept is surfaced, not stored in a state
    # that would crash the strict show/list serialisation.
    _run_with_board("broken", _complete_map(view={"type": "not-a-real-view"}))

    assert get_own_map(admin, "broken") is None
    assert "broken" not in _outcomes()


def test_a_board_fixed_after_a_failed_run_is_migrated(admin: UserId) -> None:
    _run_with_board("broken", _complete_map(view={"type": "not-a-real-view"}))
    _run_with_board("broken", _complete_map())

    assert get_own_map(admin, "broken") is not None
    assert _outcomes()["broken"] == "migrated"


@_NOT_ROOT
@pytest.mark.usefixtures("with_admin")
def test_an_unreadable_board_is_left_for_a_later_run() -> None:
    locked = _write_board("locked", _complete_map())
    with _unreadable(locked):
        _run_with_board("legacy", _complete_map())

    assert _outcomes() == {"legacy": "migrated"}


@pytest.mark.usefixtures("with_admin")
def test_a_board_with_an_invalid_map_name_is_left_for_a_later_run() -> None:
    _run_with_board("my.map", _complete_map())

    assert "my.map" not in _outcomes()


def test_a_demo_board_is_recorded_as_skipped(admin: UserId) -> None:
    _run_with_board("demo-static", _complete_map(readonly=True))

    assert get_own_map(admin, "demo-static") is None
    assert _outcomes()["demo-static"] == "skipped"


def test_a_board_named_like_one_of_the_admin_gets_the_fallback_name(admin: UserId) -> None:
    _run_with_board("dup", _complete_map(alias="First"))
    store.save_object_to_file(_record_path(), {})
    _run_with_board("dup", _complete_map(alias="Second"))

    page = get_own_map(admin, "dup_legacy")
    assert page is not None
    assert page.config.map_spec["alias"] == "Second"
    assert _outcomes()["dup"] == "migrated"


def test_existing_map_keeps_its_content(admin: UserId) -> None:
    _migrated(admin, "dup", _complete_map(alias="First"))
    store.save_object_to_file(_record_path(), {})
    _run_with_board("dup", _complete_map(alias="Second"))

    page = get_own_map(admin, "dup")
    assert page is not None
    assert page.config.map_spec["alias"] == "First"


def test_a_board_stored_by_a_stopped_run_is_recorded_as_migrated(admin: UserId) -> None:
    _migrated(admin, "legacy", _complete_map())
    store.save_object_to_file(_record_path(), {"pending": {"legacy": "legacy"}})

    _action()(_LOGGER)

    assert _outcomes() == {"legacy": "migrated"}


def test_a_board_a_stopped_run_did_not_store_is_migrated_again(admin: UserId) -> None:
    store.save_object_to_file(_record_path(), {"pending": {"legacy": "legacy"}})

    _migrated(admin, "legacy", _complete_map())

    assert _outcomes() == {"legacy": "migrated"}


def test_a_board_named_like_a_builtin_map_gets_a_fallback_name(admin: UserId) -> None:
    # In OrbVis "infrastructure" was just a board name; in Maps a built-in has it.
    _run_with_board("infrastructure", _complete_map(alias="Our infrastructure"))

    page = get_own_map(admin, "infrastructure_legacy")
    assert page is not None
    assert page.config.map_spec["alias"] == "Our infrastructure"


def test_a_board_named_like_a_builtin_map_does_not_shadow_it(admin: UserId) -> None:
    # The admin's own map would take the built-in's place for the admin.
    _run_with_board("infrastructure", _complete_map())

    assert get_own_map(admin, "infrastructure") is None


@pytest.mark.usefixtures("with_admin")
def test_the_fallback_name_keeps_the_boards_visibility() -> None:
    _set_role_permissions("user", {"orbvis.view_all": False, "orbvis.view_infrastructure": False})
    _run_with_board("infrastructure", _complete_map())

    assert _role_permissions("user")["map.infrastructure_legacy"] is False


def test_a_taken_fallback_name_is_recorded_as_skipped(admin: UserId) -> None:
    # Not imported over the map of the fallback name.
    save_user_file("user_maps", {"infrastructure_legacy": {"title": "Taken"}}, admin)
    _run_with_board("infrastructure", _complete_map())

    assert _outcomes()["infrastructure"] == "skipped"


def test_a_board_named_like_another_users_map_gets_a_fallback_name(
    load_config: Config,
    admin: UserId,
) -> None:
    # One map.<name> permission per name: the board must not share it with bob's map.
    with create_and_destroy_user(username="bob", config=load_config):
        save_user_file("user_maps", {"dc1": {"title": "Bob's"}}, UserId("bob"))
        _run_with_board("dc1", _complete_map())

        assert get_own_map(admin, "dc1") is None
        assert get_own_map(admin, "dc1_legacy") is not None


def test_a_long_name_is_shortened_for_its_fallback(load_config: Config, admin: UserId) -> None:
    board = "a" * 100
    with create_and_destroy_user(username="bob", config=load_config):
        save_user_file("user_maps", {board: {"title": "Bob's"}}, UserId("bob"))
        _run_with_board(board, _complete_map())

        assert get_own_map(admin, "a" * 93 + "_legacy") is not None


@pytest.mark.usefixtures("with_admin")
def test_the_visibility_of_a_board_leaves_another_users_map_alone(load_config: Config) -> None:
    _set_role_permissions("user", {"orbvis.view_all": False, "orbvis.view_dc1": False})
    with create_and_destroy_user(username="bob", config=load_config):
        save_user_file("user_maps", {"dc1": {"title": "Bob's"}}, UserId("bob"))
        _run_with_board("dc1", _complete_map())

        assert "map.dc1" not in _role_permissions("user")


def test_a_stored_map_that_no_longer_loads_survives_the_migration(admin: UserId) -> None:
    # The GUI skips a stored map it cannot load; the migration must not write the
    # admin's store back without it.
    save_user_file("user_maps", {"stale": {"title": "No longer a valid map"}}, admin)

    _migrated(admin, "legacy3", _complete_map())

    assert (admin, "stale") in MapPage.load_raw()


@_NOT_ROOT
def test_failed_store_write_records_nothing_for_retry(admin: UserId) -> None:
    _write_board("fragile", _complete_map(alias="Fragile"))
    _run_with_failing_store(admin)

    assert "fragile" not in _outcomes()
    assert get_own_map(admin, "fragile") is None


@_NOT_ROOT
def test_the_copied_icons_are_recorded_when_the_maps_are_not_stored(admin: UserId) -> None:
    _write_legacy_file("images/rack.png", _PNG)
    _write_board("fragile", _complete_map())
    _run_with_failing_store(admin)

    assert _copied_icons() == {"rack.png": "rack.png"}


@_NOT_ROOT
def test_the_backgrounds_of_boards_not_stored_are_dropped(admin: UserId) -> None:
    # The next run may store the maps for another owner, which would orphan them.
    _write_legacy_file("boards/backgrounds/floor.png", _PNG)
    _write_board("fragile", _complete_map(background_image="floor.png"))
    _run_with_failing_store(admin)

    assert list(_maps_backgrounds_dir().glob("*")) == []


@_NOT_ROOT
def test_visibility_is_settled_before_the_map_is_stored(admin: UserId) -> None:
    # A map must never be published before its roles are restricted: a run that
    # stops in between would otherwise leave it open, as the next run skips it.
    _write_board("fragile", _complete_map())
    _run_with_failing_store(admin)

    assert _role_permissions("guest")["map.fragile"] is False
