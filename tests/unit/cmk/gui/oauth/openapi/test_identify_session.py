#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import copy
import json
from http import HTTPStatus

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.oauth.token.token_store import get_token_store
from cmk.gui.type_defs import SessionState
from cmk.gui.userdb import load_session_infos
from cmk.gui.userdb.session import auth_cookie_value, create_session_id
from tests.testlib.unit.fake_site import LoggedSecurityEvent
from tests.testlib.unit.gui.gui_session_endpoints import SessionCookieFactory
from tests.testlib.unit.gui.users import create_and_destroy_user
from tests.testlib.unit.gui.web_test_app import SetConfig
from tests.testlib.unit.rest_api_client import ClientRegistry, Response


def _assert_invalid_grant(resp: Response) -> None:
    resp.assert_status_code(HTTPStatus.BAD_REQUEST)
    assert resp.json["ext"] == {"error": "invalid_grant"}


def test_identify_answers_only_the_user_of_a_live_session(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)

    resp = clients.GuiSession.identify({"session_cookie": cookie}, headers=internal_token)

    assert resp.json == {"user_id": user_id}


def test_identify_issues_no_token(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
    security_events: list[LoggedSecurityEvent],
) -> None:
    """Only the delegate endpoint issues tokens"""
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)

    clients.GuiSession.identify({"session_cookie": cookie}, headers=internal_token)

    with get_token_store() as tokens:
        assert tokens.list_all_usable_grants() == []
    assert [e for e in security_events if e.summary == "oauth token issued"] == []


def test_identify_refuses_a_wrong_site_internal_secret(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)
    wrong_secret = base64.b64encode(b"not the site secret").decode()

    resp = clients.GuiSession.identify(
        {"session_cookie": cookie},
        headers={"Authorization": f"InternalToken {wrong_secret}"},
        expect_ok=False,
    )

    resp.assert_status_code(HTTPStatus.UNAUTHORIZED)


def test_identify_refuses_a_caller_that_is_authenticated_otherwise(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)

    # Without overriding the Authorization header it
    # falls back to the bearer header added by the clients fixture.
    resp = clients.GuiSession.identify({"session_cookie": cookie}, expect_ok=False)

    resp.assert_status_code(HTTPStatus.UNAUTHORIZED)


def test_identify_refuses_the_caller_before_looking_at_the_cookie(
    clients: ClientRegistry,
) -> None:
    resp = clients.GuiSession.identify({"session_cookie": "not a cookie"}, expect_ok=False)

    resp.assert_status_code(HTTPStatus.UNAUTHORIZED)


def test_identify_rejects_a_cookie_that_does_not_parse(
    clients: ClientRegistry, internal_token: dict[str, str]
) -> None:
    resp = clients.GuiSession.identify(
        {"session_cookie": "not a cookie"}, headers=internal_token, expect_ok=False
    )

    _assert_invalid_grant(resp)


def test_identify_rejects_a_cookie_with_a_wrong_signature(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    session_id, _cookie = make_session_cookie(user_id)

    resp = clients.GuiSession.identify(
        {"session_cookie": f"{user_id}:{session_id}:{'0' * 64}"},
        headers=internal_token,
        expect_ok=False,
    )

    _assert_invalid_grant(resp)


def test_identify_rejects_a_cookie_for_an_unknown_session(
    clients: ClientRegistry, with_user: tuple[UserId, str], internal_token: dict[str, str]
) -> None:
    user_id, _password = with_user
    cookie = auth_cookie_value(user_id, create_session_id())

    resp = clients.GuiSession.identify(
        {"session_cookie": cookie}, headers=internal_token, expect_ok=False
    )

    _assert_invalid_grant(resp)


@pytest.mark.parametrize(
    "state",
    [
        "credentials_needed",
        "second_factor_auth_needed",
        "second_factor_setup_needed",
        "password_change_needed",
    ],
)
def test_identify_rejects_a_session_that_is_not_fully_logged_in(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
    state: SessionState,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id, state=state)

    resp = clients.GuiSession.identify(
        {"session_cookie": cookie}, headers=internal_token, expect_ok=False
    )

    _assert_invalid_grant(resp)


def test_identify_rejects_a_session_past_its_idle_timeout(
    clients: ClientRegistry,
    set_config: SetConfig,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id, idle_seconds=7200)

    with set_config(session_mgmt={"user_idle_timeout": 3600}):
        resp = clients.GuiSession.identify(
            {"session_cookie": cookie}, headers=internal_token, expect_ok=False
        )

    _assert_invalid_grant(resp)


def test_identify_rejects_a_session_past_its_maximum_duration(
    clients: ClientRegistry,
    set_config: SetConfig,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id, age_seconds=7200)

    with set_config(session_mgmt={"max_duration": {"enforce_reauth": 3600}}):
        resp = clients.GuiSession.identify(
            {"session_cookie": cookie}, headers=internal_token, expect_ok=False
        )

    _assert_invalid_grant(resp)


def test_identify_leaves_the_last_activity_of_the_session_unchanged(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    session_id, cookie = make_session_cookie(user_id, idle_seconds=60)
    before = load_session_infos(user_id)[session_id].last_activity

    clients.GuiSession.identify({"session_cookie": cookie}, headers=internal_token)

    assert load_session_infos(user_id)[session_id].last_activity == before


def test_identify_rejects_the_session_of_a_locked_user(
    clients: ClientRegistry,
    load_config: Config,
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    with create_and_destroy_user(custom_attrs={"locked": True}, config=load_config) as (
        user_id,
        _password,
    ):
        _session_id, cookie = make_session_cookie(user_id)

        resp = clients.GuiSession.identify(
            {"session_cookie": cookie}, headers=internal_token, expect_ok=False
        )

    _assert_invalid_grant(resp)


def test_identify_rejects_the_session_of_a_user_without_gui_access(
    clients: ClientRegistry,
    set_config: SetConfig,
    load_config: Config,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)
    roles = copy.deepcopy(load_config.roles)
    roles["user"]["permissions"] = {**roles["user"].get("permissions", {}), "general.use": False}

    with set_config(roles=roles):
        resp = clients.GuiSession.identify(
            {"session_cookie": cookie}, headers=internal_token, expect_ok=False
        )

    _assert_invalid_grant(resp)


def test_identify_rejects_a_body_without_a_session_cookie(
    clients: ClientRegistry, internal_token: dict[str, str]
) -> None:
    resp = clients.GuiSession.identify({}, headers=internal_token, expect_ok=False)

    resp.assert_status_code(HTTPStatus.BAD_REQUEST)
    assert "ext" not in resp.json


def test_identify_rejects_a_body_with_unknown_fields(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)

    resp = clients.GuiSession.identify(
        {"session_cookie": cookie, "subject_token_type": "urn:example"},
        headers=internal_token,
        expect_ok=False,
    )

    resp.assert_status_code(HTTPStatus.BAD_REQUEST)
    assert "ext" not in resp.json


@pytest.mark.parametrize(
    "permission, held",
    [
        pytest.param("general.use", True, id="granted by the defaults of the role"),
        pytest.param("wato.users", False, id="not granted to the role"),
        pytest.param("general.no_such_permission", False, id="not registered"),
    ],
)
def test_identify_reports_whether_the_user_holds_a_permission(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
    permission: str,
    held: bool,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)

    resp = clients.GuiSession.identify(
        {"session_cookie": cookie, "required_permissions": [permission]}, headers=internal_token
    )

    assert resp.json == {"user_id": user_id, "permissions": {permission: held}}


def test_identify_reports_an_unregistered_permission_as_not_held_even_if_a_role_grants_it(
    clients: ClientRegistry,
    set_config: SetConfig,
    load_config: Config,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    """A role keeps a saved grant after its permission is no longer registered"""
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)
    roles = copy.deepcopy(load_config.roles)
    roles["user"]["permissions"] = {
        **roles["user"].get("permissions", {}),
        "general.no_such_permission": True,
    }

    with set_config(roles=roles):
        resp = clients.GuiSession.identify(
            {"session_cookie": cookie, "required_permissions": ["general.no_such_permission"]},
            headers=internal_token,
        )

    assert resp.json["permissions"] == {"general.no_such_permission": False}


def test_identify_reports_each_requested_permission_once(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)

    resp = clients.GuiSession.identify(
        {
            "session_cookie": cookie,
            "required_permissions": ["general.use", "wato.users", "general.use"],
        },
        headers=internal_token,
    )

    assert resp.json["permissions"] == {"general.use": True, "wato.users": False}


def test_identify_reports_no_permissions_for_an_empty_list(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)

    resp = clients.GuiSession.identify(
        {"session_cookie": cookie, "required_permissions": []}, headers=internal_token
    )

    assert resp.json == {"user_id": user_id, "permissions": {}}


def test_identify_reports_no_permissions_for_a_refused_session(
    clients: ClientRegistry, with_user: tuple[UserId, str], internal_token: dict[str, str]
) -> None:
    user_id, _password = with_user
    cookie = auth_cookie_value(user_id, create_session_id())

    resp = clients.GuiSession.identify(
        {"session_cookie": cookie, "required_permissions": ["general.use"]},
        headers=internal_token,
        expect_ok=False,
    )

    _assert_invalid_grant(resp)
    assert "permissions" not in resp.json


@pytest.mark.parametrize(
    "required_permissions",
    [
        pytest.param([f"general.p{i}" for i in range(51)], id="more than 50 names"),
        pytest.param(["general." + "x" * 249], id="a name longer than 256 characters"),
        pytest.param([""], id="an empty name"),
    ],
)
def test_identify_rejects_permission_names_beyond_the_limits(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
    required_permissions: list[str],
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)

    resp = clients.GuiSession.identify(
        {"session_cookie": cookie, "required_permissions": required_permissions},
        headers=internal_token,
        expect_ok=False,
    )

    resp.assert_status_code(HTTPStatus.BAD_REQUEST)
    assert "ext" not in resp.json


def test_identify_refuses_a_caller_without_the_site_internal_secret_that_names_permissions(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)

    resp = clients.GuiSession.identify(
        {"session_cookie": cookie, "required_permissions": ["general.use"]}, expect_ok=False
    )

    resp.assert_status_code(HTTPStatus.UNAUTHORIZED)


def _rejections(security_events: list[LoggedSecurityEvent]) -> list[dict[str, object]]:
    return [dict(e.details) for e in security_events if e.summary == "gui session rejected"]


def test_identify_logs_why_it_refused_a_session(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    security_events: list[LoggedSecurityEvent],
) -> None:
    user_id, _password = with_user
    cookie = auth_cookie_value(user_id, create_session_id())

    clients.GuiSession.identify({"session_cookie": cookie}, headers=internal_token, expect_ok=False)

    assert _rejections(security_events) == [
        {"reason": "session is not logged in", "user": user_id, "endpoint": "identify"}
    ]


def test_identify_logs_no_user_for_a_cookie_that_does_not_verify(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
    security_events: list[LoggedSecurityEvent],
) -> None:
    """The user name in such a cookie is exactly the part that cannot be trusted"""
    user_id, _password = with_user
    session_id, _cookie = make_session_cookie(user_id)

    clients.GuiSession.identify(
        {"session_cookie": f"{user_id}:{session_id}:{'0' * 64}"},
        headers=internal_token,
        expect_ok=False,
    )

    assert _rejections(security_events) == [
        {"reason": "cookie does not verify", "user": "Unknown user", "endpoint": "identify"}
    ]


def test_identify_keeps_the_cookie_out_of_the_security_log(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    security_events: list[LoggedSecurityEvent],
) -> None:
    user_id, _password = with_user
    session_id = create_session_id()
    cookie = auth_cookie_value(user_id, session_id)

    clients.GuiSession.identify({"session_cookie": cookie}, headers=internal_token, expect_ok=False)

    logged = json.dumps([e.details for e in security_events])
    assert cookie.rsplit(":", 1)[-1] not in logged
    assert session_id not in logged


def test_identify_logs_no_rejection_for_a_live_session(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
    security_events: list[LoggedSecurityEvent],
) -> None:
    user_id, _password = with_user
    _session_id, cookie = make_session_cookie(user_id)

    clients.GuiSession.identify({"session_cookie": cookie}, headers=internal_token)

    assert _rejections(security_events) == []


def test_identify_answers_the_contact_groups_on_request(
    clients: ClientRegistry,
    load_config: Config,
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    with create_and_destroy_user(
        custom_attrs={"contactgroups": ["windows", "linux"]}, config=load_config
    ) as (user_id, _password):
        _session_id, cookie = make_session_cookie(user_id)

        resp = clients.GuiSession.identify(
            {"session_cookie": cookie, "include_contact_groups": True}, headers=internal_token
        )

    assert resp.json == {"user_id": user_id, "contact_groups": ["linux", "windows"]}


def test_identify_answers_no_contact_groups_unless_asked(
    clients: ClientRegistry,
    load_config: Config,
    internal_token: dict[str, str],
    make_session_cookie: SessionCookieFactory,
) -> None:
    with create_and_destroy_user(custom_attrs={"contactgroups": ["linux"]}, config=load_config) as (
        user_id,
        _password,
    ):
        _session_id, cookie = make_session_cookie(user_id)

        resp = clients.GuiSession.identify({"session_cookie": cookie}, headers=internal_token)

    assert "contact_groups" not in resp.json
