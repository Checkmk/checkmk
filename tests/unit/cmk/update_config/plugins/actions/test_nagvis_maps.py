#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.logged_in import save_user_file
from cmk.gui.userdb import UserRolesConfigFile
from cmk.gui.watolib.groups_io import load_group_information, save_group_information
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.store import get_own_map
from cmk.update_config.internal import ExpiryVersion
from cmk.update_config.plugins.actions.nagvis_maps import MigrateNagVisMaps
from cmk.utils import paths
from tests.testlib.unit.gui.users import create_and_destroy_user

_LOGGER = logging.getLogger("test-nagvis-maps-migration")

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def _record_path() -> Path:
    return paths.omd_root / "var" / "maps" / "nagvis_maps_migration.mk"


_NOT_ROOT = pytest.mark.skipif(os.getuid() == 0, reason="root reads and writes through file modes")


@pytest.fixture(name="admin")
def fixture_admin(with_admin: tuple[UserId, str]) -> UserId:
    return with_admin[0]


def _action() -> MigrateNagVisMaps:
    # As every site sets it up; ``nagvis.ini.php``, read after it, may override it.
    _write_nagvis_file(
        "conf.d/authorisation.ini.php",
        '[global]\nauthorisationmodule="CoreAuthorisationModMultisite"\n',
    )
    return MigrateNagVisMaps(
        name="migrate_nagvis_maps",
        title="test",
        sort_index=0,
        expiry_version=ExpiryVersion.NEVER,
    )


def _write_nagvis_file(relative: str, text: str) -> Path:
    path = paths.omd_root / "etc" / "nagvis" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _write_map(name: str, *blocks: str) -> Path:
    return _write_nagvis_file(f"maps/{name}.cfg", "\n".join(blocks))


_HOST = "define host {\nhost_name=web01\nx=10\ny=20\n}"


def _write_nagvis_image(kind: str, name: str, contents: bytes = _PNG) -> None:
    path = paths.omd_root / "local/share/nagvis/htdocs/userfiles/images" / kind / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)


def _migrated(admin: UserId, name: str, *blocks: str) -> MapPage:
    _write_map(name, *blocks)
    _action()(_LOGGER)
    page = get_own_map(admin, name)
    assert page is not None
    return page


def _objects(page: MapPage) -> list[dict[str, object]]:
    objects = page.config.map_spec["objects"]
    assert isinstance(objects, list)
    for obj in objects:
        assert isinstance(obj, dict)
    return objects


def _outcomes() -> Mapping[str, str]:
    record: Mapping[str, Mapping[str, str]] = store.load_object_from_file(
        _record_path(), default={}
    )
    return record.get("maps", {})


def _role_permissions(role_id: str) -> Mapping[str, bool]:
    return UserRolesConfigFile().load_for_reading()[role_id]["permissions"]


def _set_role_permissions(role_id: str, permissions: Mapping[str, bool]) -> None:
    roles_file = UserRolesConfigFile()
    roles = roles_file.load_for_modification()
    roles[role_id]["permissions"].update(permissions)
    roles_file.save(roles, pprint_value=False)


@pytest.fixture(name="ops_group")
def fixture_ops_group() -> Iterator[None]:
    """A contact group whose members NagVis shows the map ``listed``."""
    groups = load_group_information()
    groups["contact"]["ops"] = {"alias": "Ops", "nagvis_maps": ["listed"]}
    save_group_information(groups, pprint_value=False)
    yield
    del groups["contact"]["ops"]
    save_group_information(groups, pprint_value=False)


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.levelname == "WARNING"]


# --- what a map becomes -----------------------------------------------------


def test_a_nagvis_map_becomes_a_map_of_the_admin_with_its_objects(admin: UserId) -> None:
    page = _migrated(admin, "office", "define global {\nalias=Office\n}", _HOST)

    assert page.config.map_spec["alias"] == "Office"
    assert [obj["host_name"] for obj in _objects(page)] == ["web01"]


def test_the_background_is_copied_into_maps(admin: UserId) -> None:
    _write_nagvis_image("maps", "office.png")

    page = _migrated(admin, "office", "define global {\nmap_image=office.png\n}")

    stored = page.config.map_spec["background_image"]
    assert isinstance(stored, str)
    assert (paths.omd_root / "var" / "maps" / "backgrounds" / stored).read_bytes() == _PNG


def test_a_shape_is_copied_into_the_image_library(admin: UserId) -> None:
    _write_nagvis_image("shapes", "cloud.png")

    page = _migrated(admin, "office", "define shape {\nicon=cloud.png\nx=1\ny=1\n}")

    (shape,) = _objects(page)
    assert isinstance(stored := shape["image_src"], str)
    assert (paths.omd_root / "var" / "maps" / "images" / stored).read_bytes() == _PNG


def test_a_missing_shape_is_named(admin: UserId, caplog: pytest.LogCaptureFixture) -> None:
    _migrated(admin, "office", "define shape {\nicon=gone.png\nx=1\ny=1\n}")

    assert any("gone.png" in warning for warning in _warnings(caplog))


@_NOT_ROOT
def test_a_shape_is_removed_when_its_map_cannot_be_stored(admin: UserId) -> None:
    _write_nagvis_image("shapes", "cloud.png")
    _write_map("office", "define shape {\nicon=cloud.png\nx=1\ny=1\n}")
    # An existing store file: the store lock opens it, only writing it fails.
    save_user_file("user_maps", {}, admin)
    profile = paths.profile_dir / admin
    profile.chmod(0o500)
    try:
        with pytest.raises(MKGeneralException):
            _action()(_LOGGER)
    finally:
        profile.chmod(0o770)

    assert not (paths.omd_root / "var" / "maps" / "images" / "cloud.png").exists()


@_NOT_ROOT
def test_a_shape_in_the_library_before_stays_when_its_map_cannot_be_stored(
    admin: UserId,
) -> None:
    library_image = paths.omd_root / "var" / "maps" / "images" / "cloud.png"
    library_image.parent.mkdir(parents=True, exist_ok=True)
    library_image.write_bytes(_PNG)
    _write_nagvis_image("shapes", "cloud.png")
    _write_map("office", "define shape {\nicon=cloud.png\nx=1\ny=1\n}")
    save_user_file("user_maps", {}, admin)
    profile = paths.profile_dir / admin
    profile.chmod(0o500)
    try:
        with pytest.raises(MKGeneralException):
            _action()(_LOGGER)
    finally:
        profile.chmod(0o770)

    assert library_image.read_bytes() == _PNG


def test_a_gif_shape_is_named_for_conversion(
    admin: UserId, caplog: pytest.LogCaptureFixture
) -> None:
    _write_nagvis_image("shapes", "router.gif", b"GIF89a" + b"\x00" * 16)

    _migrated(admin, "office", "define shape {\nicon=router.gif\nx=1\ny=1\n}")

    assert any("router.gif" in w and "Convert them to PNG" in w for w in _warnings(caplog))


def test_a_geographic_map_is_named_for_its_markers(
    admin: UserId, caplog: pytest.LogCaptureFixture
) -> None:
    _migrated(admin, "world", "define global {\nsources=worldmap\n}")

    assert any("not migrated" in warning for warning in _warnings(caplog))


# --- runs -------------------------------------------------------------------


def test_a_migrated_map_is_not_overwritten_later(admin: UserId) -> None:
    _migrated(admin, "office", "define global {\nalias=First\n}")
    _write_map("office", "define global {\nalias=Second\n}")

    _action()(_LOGGER)

    page = get_own_map(admin, "office")
    assert page is not None
    assert page.config.map_spec["alias"] == "First"


def test_a_map_named_like_one_of_the_admin_gets_the_fallback_name(admin: UserId) -> None:
    _write_map("office", "define global {\nalias=First\n}")
    _action()(_LOGGER)
    store.save_object_to_file(_record_path(), {})
    _write_map("office", "define global {\nalias=Second\n}")

    _action()(_LOGGER)

    page = get_own_map(admin, "office_legacy")
    assert page is not None
    assert page.config.map_spec["alias"] == "Second"


@pytest.mark.usefixtures("with_admin")
def test_a_map_whose_fallback_name_is_taken_too_is_skipped() -> None:
    _write_map("office", _HOST)
    _write_map("office_legacy", _HOST)
    _action()(_LOGGER)
    store.save_object_to_file(_record_path(), {})

    _action()(_LOGGER)

    assert _outcomes()["office"] == "skipped"


def test_a_map_name_maps_does_not_take_is_cleaned(admin: UserId) -> None:
    _write_map("core.switches", _HOST)

    _action()(_LOGGER)

    assert get_own_map(admin, "core_switches") is not None
    assert _outcomes() == {"core.switches": "migrated"}


def test_a_cleaned_name_that_is_taken_names_each_step(
    admin: UserId, caplog: pytest.LogCaptureFixture
) -> None:
    save_user_file("user_maps", {"core_switches": {"title": "Own"}}, admin)
    _write_map("core.switches", _HOST)

    _action()(_LOGGER)

    assert get_own_map(admin, "core_switches_legacy") is not None
    warnings = _warnings(caplog)
    assert any("Its name becomes 'core_switches'" in warning for warning in warnings)
    assert any("migrated as 'core_switches_legacy'" in warning for warning in warnings)


def test_a_long_name_is_shortened_for_its_fallback(admin: UserId) -> None:
    name = "a" * 100
    save_user_file("user_maps", {name: {"title": "Own"}}, admin)
    _write_map(name, _HOST)

    _action()(_LOGGER)

    assert _outcomes() == {name: "migrated"}
    assert get_own_map(admin, "a" * 93 + "_legacy") is not None


@_NOT_ROOT
@pytest.mark.usefixtures("with_admin")
def test_an_unreadable_map_is_left_for_a_later_run() -> None:
    locked = _write_map("locked", _HOST)
    locked.chmod(0o000)
    try:
        _write_map("office", _HOST)
        _action()(_LOGGER)
    finally:
        locked.chmod(0o600)

    assert _outcomes() == {"office": "migrated"}


def test_a_map_stored_by_a_stopped_run_is_recorded_as_migrated(admin: UserId) -> None:
    _migrated(admin, "office", _HOST)
    store.save_object_to_file(_record_path(), {"maps": {}, "pending": {"office": "office"}})

    _action()(_LOGGER)

    assert _outcomes() == {"office": "migrated"}
    assert get_own_map(admin, "office_legacy") is None


def test_a_map_a_stopped_run_did_not_store_is_migrated_again(admin: UserId) -> None:
    store.save_object_to_file(_record_path(), {"maps": {}, "pending": {"office": "office"}})

    _migrated(admin, "office", _HOST)

    assert _outcomes() == {"office": "migrated"}


# --- who sees it ------------------------------------------------------------


def test_a_map_no_contact_group_lists_is_published_to_all(admin: UserId) -> None:
    page = _migrated(admin, "office", _HOST)

    assert page.config.public is True


def test_a_role_seeing_maps_only_by_contact_group_does_not_see_an_unlisted_map(
    admin: UserId,
) -> None:
    _migrated(admin, "office", _HOST)

    # ``user`` has ``nagvis.Map_view`` only.
    assert _role_permissions("user")["map.office"] is False
    assert "map.office" not in _role_permissions("guest")


@pytest.mark.usefixtures("ops_group")
def test_a_map_a_contact_group_lists_is_published_to_that_group(admin: UserId) -> None:
    page = _migrated(admin, "listed", _HOST)

    assert page.config.public == ("contact_groups", ["ops"])
    assert "map.listed" not in _role_permissions("user")


@pytest.mark.usefixtures("ops_group")
def test_roles_seeing_every_map_outside_the_group_are_named(
    admin: UserId, caplog: pytest.LogCaptureFixture
) -> None:
    _migrated(admin, "listed", _HOST)

    assert any("admin, guest" in warning and "ops" in warning for warning in _warnings(caplog))


def test_maps_stay_private_without_the_checkmk_authorisation(
    admin: UserId, caplog: pytest.LogCaptureFixture
) -> None:
    _write_nagvis_file(
        "nagvis.ini.php", '[global]\nauthorisationmodule="CoreAuthorisationModSQLite"\n'
    )

    page = _migrated(admin, "office", _HOST)

    assert page.config.public is False
    assert "map.office" not in _role_permissions("user")
    assert any("visible only to" in warning for warning in _warnings(caplog))


def test_a_private_map_drops_a_stale_entry_of_its_name(admin: UserId) -> None:
    _set_role_permissions("guest", {"map.office": True})
    _write_nagvis_file(
        "nagvis.ini.php", '[global]\nauthorisationmodule="CoreAuthorisationModSQLite"\n'
    )

    _migrated(admin, "office", _HOST)

    assert "map.office" not in _role_permissions("guest")


def test_a_role_without_maps_access_is_named(
    admin: UserId, caplog: pytest.LogCaptureFixture
) -> None:
    _set_role_permissions("guest", {"maps.use": False})

    _migrated(admin, "office", _HOST)

    assert any(
        "guest" in warning and "Use Checkmk Maps" in warning for warning in _warnings(caplog)
    )


def test_the_maps_of_another_admin_are_named(
    load_config: Config, caplog: pytest.LogCaptureFixture
) -> None:
    with create_and_destroy_user(username="bob", role="admin", config=load_config):
        _write_map("office", _HOST)
        _action()(_LOGGER)

        assert get_own_map(UserId("bob"), "office") is not None
    assert any("Deleting bob" in warning for warning in _warnings(caplog))


# --- rotation pools ---------------------------------------------------------


def test_a_map_takes_part_in_the_pools_that_list_it(admin: UserId) -> None:
    _write_nagvis_file("nagvis.ini.php", '[rotation_wall]\nmaps="Office:office,other"\n')

    page = _migrated(admin, "office", _HOST)

    assert page.config.map_spec["rotation_pools"] == ["wall"]


def test_a_map_rotates_at_the_interval_of_its_pool(admin: UserId) -> None:
    _write_nagvis_file("nagvis.ini.php", '[rotation_wall]\nmaps="office"\ninterval=15\n')

    page = _migrated(admin, "office", _HOST)

    assert page.config.map_spec["rotation_interval"] == 15


def test_a_pool_without_an_interval_rotates_at_the_refresh_time(admin: UserId) -> None:
    _write_nagvis_file(
        "nagvis.ini.php", '[global]\nrefreshtime=20\n[rotation_wall]\nmaps="office"\n'
    )

    page = _migrated(admin, "office", _HOST)

    assert page.config.map_spec["rotation_interval"] == 20


def test_a_pool_at_the_maps_default_interval_leaves_the_map_still_outside_it(
    admin: UserId,
) -> None:
    _write_nagvis_file("nagvis.ini.php", '[rotation_wall]\nmaps="office"\ninterval=60\n')

    page = _migrated(admin, "office", _HOST)

    assert page.config.map_spec["rotation_interval"] == 0


def test_differing_pool_intervals_take_the_shortest_and_are_named(
    admin: UserId, caplog: pytest.LogCaptureFixture
) -> None:
    _write_nagvis_file(
        "nagvis.ini.php",
        '[rotation_a]\nmaps="office"\ninterval=30\n[rotation_b]\nmaps="office"\ninterval=10\n',
    )

    page = _migrated(admin, "office", _HOST)

    assert page.config.map_spec["rotation_interval"] == 10
    assert any("10, 30 seconds" in warning for warning in _warnings(caplog))


def test_a_url_in_a_pool_is_named(admin: UserId, caplog: pytest.LogCaptureFixture) -> None:
    _write_nagvis_file(
        "nagvis.ini.php", '[rotation_wall]\nmaps="office,Status:[https://status.example]"\n'
    )

    _migrated(admin, "office", _HOST)

    assert any("https://status.example" in warning for warning in _warnings(caplog))


def test_conf_d_pools_are_read_before_the_main_file(admin: UserId) -> None:
    _write_nagvis_file("conf.d/pools.ini.php", '[rotation_wall]\nmaps="office"\ninterval=15\n')
    _write_nagvis_file("nagvis.ini.php", "[rotation_wall]\ninterval=25\n")

    page = _migrated(admin, "office", _HOST)

    assert page.config.map_spec["rotation_interval"] == 25
