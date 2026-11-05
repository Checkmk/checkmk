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
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.utils.local_secrets import SiteInternalSecret
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


def test_an_image_in_use_is_kept_with_the_maps_using_it(clients: ClientRegistry) -> None:
    clients.Maps.upload_image("rack.png", "image/png", _PNG)
    clients.Maps.create(config=_map("floor", background_image="rack.png"))

    resp = clients.Maps.delete_image("rack.png", expect_ok=False)

    resp.assert_status_code(HTTPStatus.CONFLICT)
    assert resp.json["ext"]["usage"] == [
        {"map": "floor", "alias": "Floor", "object_ids": [], "is_background": True}
    ]


def test_a_background_is_stored_for_its_map(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_map("floor"))
    filename = clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG).json[
        "filename"
    ]
    assert filename.endswith(".png")


def test_a_background_is_removed(clients: ClientRegistry) -> None:
    clients.Maps.create(config=_map("floor"))
    clients.Maps.upload_background("floor", "plan.png", "image/png", _PNG)
    clients.Maps.delete_background("floor").assert_status_code(HTTPStatus.NO_CONTENT)


def test_a_nagvis_cfg_parses_into_a_draft(clients: ClientRegistry) -> None:
    assert clients.Maps.parse_cfg("floor.cfg", _CFG).json["map"]["alias"] == "Imported"
