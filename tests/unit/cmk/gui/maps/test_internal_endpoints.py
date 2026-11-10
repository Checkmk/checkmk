#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Maps SPA's internal endpoints, called the way the SPA calls them.

Going through the WSGI app matters here: the framework's permission tracker
raises in tests for any permission an endpoint checks without declaring it, so
each test here also pins its endpoint's declaration.
"""

import copy
from http import HTTPStatus

import pytest

import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.type_defs import UserSpec
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.utils.local_secrets import SiteInternalSecret
from tests.testlib.unit.gui.users import create_and_destroy_user
from tests.testlib.unit.gui.web_test_app import SetConfig
from tests.testlib.unit.rest_api_client import ClientRegistry

# Enough of a PNG for the magic-byte check.
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16

_CFG = b"define global {\nalias=Imported\n}\n\ndefine host {\nhost_name=heute\nx=10\ny=20\n}\n"


def _map(name: str, **overrides: object) -> dict[str, object]:
    return {
        "name": name,
        "alias": name.title(),
        "connection_id": "live_1",
        "icon_size": None,
        "rotation_interval": 0,
        "sort_order": 0,
        "click_action": "link",
        "view": {"type": "static"},
        "objects": [],
        **overrides,
    }


def _internal_token() -> dict[str, str]:
    """The Authorization header the Maps daemon sends."""
    return {"Authorization": f"InternalToken {SiteInternalSecret().secret.b64_str}"}


def test_session_carries_the_capabilities(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> None:
    resp = clients.Maps.get_session()
    assert resp.json["user_id"] == with_automation_user[0]
    assert "force_check" in resp.json["capabilities"]["commands"]


def test_access_names_the_empty_owner_of_a_built_in_map(
    clients: ClientRegistry, with_user: tuple[UserId, str]
) -> None:
    resp = clients.Maps.resolve_access(
        {"user_id": with_user[0], "name": "all_hosts"}, headers=_internal_token()
    )
    assert resp.json == {"owner": ""}


def test_access_names_the_owner_of_an_own_map(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> None:
    clients.Maps.create(config=_map("floor"))
    resp = clients.Maps.resolve_access(
        {"user_id": with_automation_user[0], "name": "floor"}, headers=_internal_token()
    )
    assert resp.json == {"owner": with_automation_user[0]}


def test_access_names_no_owner_for_a_private_map_of_someone_else(
    clients: ClientRegistry, with_user: tuple[UserId, str]
) -> None:
    clients.Maps.create(config=_map("floor"))
    resp = clients.Maps.resolve_access(
        {"user_id": with_user[0], "name": "floor"}, headers=_internal_token()
    )
    assert resp.json == {}


def test_access_is_reserved_for_the_site(
    clients: ClientRegistry, with_user: tuple[UserId, str]
) -> None:
    resp = clients.Maps.resolve_access(
        {"user_id": with_user[0], "name": "all_hosts"}, expect_ok=False
    )
    resp.assert_status_code(HTTPStatus.UNAUTHORIZED)


def _link_targets(resp_json: dict[str, list[dict[str, str]]]) -> dict[str, tuple[str, bool]]:
    return {t["name"]: (t["owner"], "config_b64" in t) for t in resp_json["targets"]}


def test_link_targets_are_the_maps_the_user_sees_with_their_config(
    clients: ClientRegistry, with_user: tuple[UserId, str]
) -> None:
    clients.Maps.create(
        config=_map("shared"), visibility={"publish": "all", "hide_in_monitor_menu": False}
    )
    clients.Maps.create(config=_map("private"))
    resp = clients.Maps.resolve_link_targets(
        {"user_id": with_user[0], "names": ["shared", "private", "all_hosts", "missing"]},
        headers=_internal_token(),
    )
    automation_user = clients.Maps.get("shared").json["extensions"]["owner"]
    assert _link_targets(resp.json) == {"shared": (automation_user, True), "all_hosts": ("", True)}


def test_a_link_target_the_daemon_holds_comes_without_its_config(
    clients: ClientRegistry, with_user: tuple[UserId, str]
) -> None:
    resp = clients.Maps.resolve_link_targets(
        {
            "user_id": with_user[0],
            "names": ["all_hosts"],
            "cached": [{"owner": "", "name": "all_hosts"}],
        },
        headers=_internal_token(),
    )
    assert _link_targets(resp.json) == {"all_hosts": ("", False)}


@pytest.mark.usefixtures("with_automation_user")
def test_link_targets_without_a_user_are_built_in_maps_only(clients: ClientRegistry) -> None:
    clients.Maps.create(
        config=_map("floor"), visibility={"publish": "all", "hide_in_monitor_menu": False}
    )
    resp = clients.Maps.resolve_link_targets(
        {"names": ["floor", "all_hosts"]}, headers=_internal_token()
    )
    assert _link_targets(resp.json) == {"all_hosts": ("", True)}


def test_link_targets_of_a_user_who_is_gone_are_none(clients: ClientRegistry) -> None:
    resp = clients.Maps.resolve_link_targets(
        {"user_id": "gone", "names": ["all_hosts"]}, headers=_internal_token()
    )
    assert resp.json == {"targets": []}


def test_link_targets_are_reserved_for_the_site(
    clients: ClientRegistry, with_user: tuple[UserId, str]
) -> None:
    resp = clients.Maps.resolve_link_targets(
        {"user_id": with_user[0], "names": ["all_hosts"]}, expect_ok=False
    )
    resp.assert_status_code(HTTPStatus.UNAUTHORIZED)


@pytest.mark.parametrize(
    "sites", [pytest.param(["remote", "central"], id="some"), pytest.param(None, id="all")]
)
def test_monitored_sites_are_those_set_for_the_user(
    clients: ClientRegistry, load_config: Config, sites: list[str] | None
) -> None:
    custom_attrs: UserSpec = (
        {} if sites is None else {"authorized_sites": [SiteId(site) for site in sites]}
    )
    with create_and_destroy_user(custom_attrs=custom_attrs, config=load_config) as (
        user_id,
        _password,
    ):
        resp = clients.Maps.show_monitored_sites({"user_id": user_id}, headers=_internal_token())

    assert resp.json == {"monitored_sites": None if sites is None else sorted(sites)}


def test_monitored_sites_of_a_user_who_is_gone_are_not_named(clients: ClientRegistry) -> None:
    resp = clients.Maps.show_monitored_sites(
        {"user_id": "gone"}, headers=_internal_token(), expect_ok=False
    )
    resp.assert_status_code(HTTPStatus.NOT_FOUND)


def test_monitored_sites_are_reserved_for_the_site(
    clients: ClientRegistry, with_user: tuple[UserId, str]
) -> None:
    resp = clients.Maps.show_monitored_sites({"user_id": with_user[0]}, expect_ok=False)
    resp.assert_status_code(HTTPStatus.UNAUTHORIZED)


@pytest.mark.usefixtures("request_context")
def test_force_check_reschedules_the_host(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_FORCED_HOST_CHECK;heute;...", match_type="ellipsis"
    )
    with mock_livestatus:
        clients.Maps.run_command({"action": "force_check", "host_name": "heute"})


@pytest.mark.usefixtures("request_context")
def test_disable_checks_goes_to_the_objects_site(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    set_config: SetConfig,
    load_config: Config,
) -> None:
    # No role has the toggle's permission by default, not even the admin.
    roles = copy.deepcopy(load_config.roles)
    roles["admin"]["permissions"] = {
        **roles["admin"].get("permissions", {}),
        "action.enablechecks": True,
    }
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name\nFilter: name = heute", sites=["NO_SITE"]
    )
    mock_livestatus.expect_query(
        "COMMAND [...] DISABLE_HOST_CHECK;heute", match_type="ellipsis", sites=["NO_SITE"]
    )
    with set_config(roles=roles), mock_livestatus:
        clients.Maps.run_command(
            {"action": "disable_checks", "host_name": "heute", "site_id": "NO_SITE"}
        )


def test_a_verb_the_rest_api_offers_is_not_run_here(clients: ClientRegistry) -> None:
    clients.Maps.run_command(
        {"action": "acknowledge", "host_name": "heute"}, expect_ok=False
    ).assert_status_code(HTTPStatus.BAD_REQUEST)


def test_form_schema_renders_the_dialog(clients: ClientRegistry) -> None:
    assert clients.Maps.get_form_schema("flow_view").json["schema"]


def test_form_values_parse_back(clients: ClientRegistry) -> None:
    data = clients.Maps.get_form_schema("flow_view").json["data"]
    assert "data" in clients.Maps.parse_form("flow_view", data).json


def test_an_uploaded_image_joins_the_library(clients: ClientRegistry) -> None:
    assert clients.Maps.upload_image("rack.png", "image/png", _PNG).json["name"] == "rack.png"


def test_the_image_library_is_not_listed_for_a_guest(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    with_automation_user_guest: tuple[UserId, str],
) -> None:
    clients.Maps.set_credentials(*map(str, with_automation_user_guest))
    try:
        resp = clients.Maps.get_images(expect_ok=False)
    finally:
        clients.Maps.set_credentials(*map(str, with_automation_user))

    resp.assert_status_code(HTTPStatus.FORBIDDEN)


def test_the_image_library_is_listed_for_an_editor_of_the_maps_of_others(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    with_automation_user_guest: tuple[UserId, str],
    set_config: SetConfig,
    load_config: Config,
) -> None:
    roles = copy.deepcopy(load_config.roles)
    roles["guest"]["permissions"] = {
        **roles["guest"].get("permissions", {}),
        "general.edit_foreign_map": True,
    }
    clients.Maps.set_credentials(*map(str, with_automation_user_guest))
    try:
        with set_config(roles=roles):
            resp = clients.Maps.get_images()
    finally:
        clients.Maps.set_credentials(*map(str, with_automation_user))

    assert resp.json["images"]


def test_an_unused_image_is_deleted(clients: ClientRegistry) -> None:
    clients.Maps.upload_image("rack.png", "image/png", _PNG)
    clients.Maps.delete_image("rack.png").assert_status_code(HTTPStatus.NO_CONTENT)


def test_a_builtin_image_is_kept(clients: ClientRegistry) -> None:
    images = clients.Maps.get_images().json["images"]
    assert any(image["name"] == "bell.svg" and image["builtin"] for image in images)

    clients.Maps.delete_image("bell.svg", expect_ok=False).assert_status_code(
        HTTPStatus.BAD_REQUEST
    )


def test_an_image_uploaded_under_a_name_a_builtin_takes_later_is_the_uploads(
    clients: ClientRegistry,
) -> None:
    images_dir = cmk.utils.paths.omd_root / "var/maps/images"
    images_dir.mkdir(parents=True, exist_ok=True)
    (images_dir / "bell.svg").write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"/>')

    images = clients.Maps.get_images().json["images"]
    assert [image["builtin"] for image in images if image["name"] == "bell.svg"] == [False]
    clients.Maps.delete_image("bell.svg").assert_status_code(HTTPStatus.NO_CONTENT)


def test_an_upload_keeps_the_image_already_under_its_name(clients: ClientRegistry) -> None:
    other = _PNG + b"\x01"
    clients.Maps.upload_image("rack 1.png", "image/png", _PNG)

    assert clients.Maps.upload_image("rack_1.png", "image/png", other).json["name"] == (
        "rack_1-2.png"
    )
    images_dir = cmk.utils.paths.omd_root / "var/maps/images"
    assert (images_dir / "rack_1.png").read_bytes() == _PNG
    assert (images_dir / "rack_1-2.png").read_bytes() == other


def test_an_image_in_use_is_kept_with_the_maps_using_it(clients: ClientRegistry) -> None:
    clients.Maps.upload_image("rack.png", "image/png", _PNG)
    rack = {
        "id": "o1",
        "type": "image",
        "position": {"x": 0, "y": 0},
        "link": {"url_target": "_blank"},
        "image_src": "rack.png",
    }
    clients.Maps.create(config=_map("floor", objects=[rack]))

    resp = clients.Maps.delete_image("rack.png", expect_ok=False)

    resp.assert_status_code(HTTPStatus.CONFLICT)
    assert resp.json["ext"]["usage"] == [
        {"map": "floor", "alias": "Floor", "object_ids": ["o1"], "is_background": False}
    ]


def _image_object(oid: str, **fields: object) -> dict[str, object]:
    return {
        "id": oid,
        "type": "image",
        "position": {"x": 0, "y": 0},
        "link": {"url_target": "_blank"},
        **fields,
    }


def test_the_icon_of_an_object_is_in_use_and_not_the_image_it_replaces(
    clients: ClientRegistry,
) -> None:
    shown = _image_object(
        "o1", image_src="replaced.png", display={"mode": "icon", "image": "rack.png"}
    )
    clients.Maps.create(config=_map("floor", objects=[shown]))

    assert clients.Maps.get_image_usage("rack.png").json == {
        "usage": [{"map": "floor", "alias": "Floor", "object_ids": ["o1"], "is_background": False}],
        "hidden_maps": 0,
    }
    assert clients.Maps.get_image_usage("replaced.png").json == {"usage": [], "hidden_maps": 0}


def test_a_map_showing_other_images_does_not_keep_an_image(clients: ClientRegistry) -> None:
    clients.Maps.upload_image("rack.png", "image/png", _PNG)
    clients.Maps.create(config=_map("floor", objects=[_image_object("o1", image_src="other.png")]))

    clients.Maps.delete_image("rack.png").assert_status_code(HTTPStatus.NO_CONTENT)


def test_a_background_is_stored_for_its_map(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_map("floor"))
    filename = clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG).json[
        "filename"
    ]
    assert filename.endswith(".png")


def test_the_last_background_stored_for_a_map_is_kept(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_map("floor"))
    clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG)
    filename = clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG).json[
        "filename"
    ]

    stored = cmk.utils.paths.omd_root / "var/maps/backgrounds"
    assert [p.name for p in stored.iterdir() if p.name.startswith(filename.split(".")[0])] == [
        filename
    ]


def test_a_background_is_removed(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_map("floor"))
    clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG)
    clients.Maps.delete_background("floor").assert_status_code(HTTPStatus.NO_CONTENT)


def _presentation_showing(image: str) -> dict[str, object]:
    transform = {
        "x": 0,
        "y": 0,
        "w": 10,
        "h": 10,
        "rotation": 0,
        "z": 0,
        "opacity": 1,
        "locked": False,
        "hidden": False,
    }
    element = {"kind": "image", "id": "e1", "transform": transform, "fit": "contain", "src": image}
    return {
        "type": "presentation",
        "width": 1920,
        "height": 1080,
        "theme": "midnight",
        "elements": [element],
        "background_image": image,
    }


def test_an_image_on_a_slide_is_in_use(clients: ClientRegistry) -> None:
    clients.Maps.upload_image("rack.png", "image/png", _PNG)
    clients.Maps.create(config=_map("slides", view=_presentation_showing("rack.png")))

    resp = clients.Maps.delete_image("rack.png", expect_ok=False)

    resp.assert_status_code(HTTPStatus.CONFLICT)
    assert resp.json["ext"]["usage"] == [
        {"map": "slides", "alias": "Slides", "object_ids": ["e1"], "is_background": True}
    ]


def test_an_image_in_a_map_the_user_does_not_see_is_counted(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    with_automation_user_not_admin: tuple[UserId, str],
) -> None:
    clients.Maps.upload_image("rack.png", "image/png", _PNG)
    clients.Maps.set_credentials(*map(str, with_automation_user_not_admin))
    try:
        clients.Maps.create(config=_map("theirs", view=_presentation_showing("rack.png")))
    finally:
        clients.Maps.set_credentials(*map(str, with_automation_user))

    resp = clients.Maps.delete_image("rack.png", expect_ok=False)

    resp.assert_status_code(HTTPStatus.CONFLICT)
    assert (resp.json["ext"]["usage"], resp.json["ext"]["hidden_maps"]) == ([], 1)


def _background_of(clients: ClientRegistry, name: str) -> str:
    background: str = clients.Maps.get(name).json["extensions"]["config"]["background_image"]
    return background


def test_a_cloned_map_keeps_its_background_when_the_source_is_deleted(
    clients: ClientRegistry,
) -> None:
    clients.Maps.create(config=_map("floor"))
    source = clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG).json["filename"]
    clients.Maps.edit("floor", _map("floor", background_image=source))

    clients.Maps.create(config=_map("copy", background_image=source))
    clients.Maps.delete("floor")

    clone = _background_of(clients, "copy")
    assert clone != source
    assert (cmk.utils.paths.omd_root / "var/maps/backgrounds" / clone).read_bytes() == _PNG


def test_a_clone_of_a_map_that_lost_its_background_has_none(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_map("floor"))
    source = clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG).json["filename"]
    clients.Maps.edit("floor", _map("floor", background_image=source))
    (cmk.utils.paths.omd_root / "var/maps/backgrounds" / source).unlink()

    clients.Maps.create(config=_map("copy", background_image=source))

    assert clients.Maps.get("copy").json["extensions"]["config"]["background_image"] is None


def test_a_background_of_no_map_the_user_sees_is_refused(clients: ClientRegistry) -> None:
    resp = clients.Maps.create(
        config=_map("floor", background_image="0123456789abcdef__other.token.png"),
        expect_ok=False,
    )

    resp.assert_status_code(HTTPStatus.BAD_REQUEST)
    assert resp.json["ext"] == {"error": "unknown_background"}


def test_a_map_created_anew_does_not_get_the_background_it_lost(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_map("floor"))
    lost = clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG).json["filename"]
    clients.Maps.edit("floor", _map("floor", background_image=lost))
    clients.Maps.delete("floor")

    resp = clients.Maps.create(config=_map("floor", background_image=lost), expect_ok=False)

    resp.assert_status_code(HTTPStatus.BAD_REQUEST)
    assert resp.json["ext"] == {"error": "unknown_background"}


def test_a_map_keeps_its_background_on_save(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_map("floor"))
    source = clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG).json["filename"]
    clients.Maps.edit("floor", _map("floor", background_image=source))

    clients.Maps.edit("floor", _map("floor", alias="Renamed", background_image=source))

    assert _background_of(clients, "floor") == source


def test_a_refused_save_keeps_the_stored_background(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_map("floor"))
    source = clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG).json["filename"]
    clients.Maps.edit("floor", _map("floor", background_image=source))
    clients.Maps.create(config=_map("copy"))
    own = clients.Maps.upload_background("copy", "own.png", "image/png", _PNG).json["filename"]
    clients.Maps.edit("copy", _map("copy", background_image=own))

    clients.Maps.edit(
        "copy", _map("copy", background_image=source), etag="invalid_etag", expect_ok=False
    ).assert_status_code(HTTPStatus.PRECONDITION_FAILED)

    assert _background_of(clients, "copy") == own
    assert (cmk.utils.paths.omd_root / "var/maps/backgrounds" / own).read_bytes() == _PNG


def test_a_nagvis_cfg_parses_into_a_draft(clients: ClientRegistry) -> None:
    assert clients.Maps.parse_cfg("floor.cfg", _CFG).json["map"]["alias"] == "Imported"


def test_a_nagvis_cfg_names_the_background_it_does_not_bring(clients: ClientRegistry) -> None:
    resp = clients.Maps.parse_cfg("floor.cfg", b"define global {\n    map_image = plan.png\n}\n")

    assert any("plan.png" in warning for warning in resp.json["warnings"])


def test_a_nagvis_cfg_draft_has_no_background_it_does_not_bring(clients: ClientRegistry) -> None:
    resp = clients.Maps.parse_cfg("floor.cfg", b"define global {\n    map_image = plan.png\n}\n")

    assert "background_image" not in resp.json["map"]


def test_a_nagvis_cfg_without_a_background_does_not_mention_one(clients: ClientRegistry) -> None:
    assert not any(
        "background" in w for w in clients.Maps.parse_cfg("floor.cfg", _CFG).json["warnings"]
    )
