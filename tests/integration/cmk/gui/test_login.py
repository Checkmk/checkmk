#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import contextlib
from collections.abc import Iterator

import pytest

from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession

from cmk.gui.type_defs import TotpCredential, TwoFactorCredentials


@pytest.fixture(name="with_automation_user")
def create_and_delete_automation_user(site: Site) -> Iterator[tuple[str, str]]:
    username = "int_test_automation_user"
    password = "longerthan10"
    site.openapi.users.create(
        username=username,
        fullname="HAL",
        password=password,
        email="auomation@localhost",
        contactgroups=[],
        roles=["user"],
        is_automation_user=True,
    )
    try:
        yield username, password
    finally:
        site.openapi.users.delete(username)


@pytest.mark.skip_if_edition("saas")
def test_login_and_logout(site: Site) -> None:
    web = CMKWebSession(site)

    r = web.get("wato.py?mode=globalvars", allow_redirect_to_login=True)
    assert "Global settings" not in r.text

    web.login()
    site.enforce_non_localized_gui(web)
    r = web.get("wato.py?mode=globalvars")
    assert "Global settings" in r.text

    web.logout()
    r = web.get("wato.py?mode=globalvars", allow_redirect_to_login=True)
    assert "Global settings" not in r.text


@pytest.mark.skip_if_edition("saas")
def test_session_cookie(site: Site) -> None:
    web = CMKWebSession(site)
    web.login()

    cookie = web.get_auth_cookie()

    assert cookie is not None
    assert cookie.path == f"/{site.id}/"
    # This is ugly but IMHO the only way...
    assert "HttpOnly" in cookie.__dict__.get("_rest", {})
    assert cookie.__dict__.get("_rest", {}).get("SameSite") == "Lax"


@pytest.mark.skip_if_edition("saas")
def test_automation_user_gui(with_automation_user: tuple[str, str], site: Site) -> None:
    """test authenticated request of an automation user to the gui

    - the HTTP param login must work in Checkmk 2.3
    - a session must not be established
    """
    username, password = with_automation_user

    session = CMKWebSession(site)
    response = session.get(
        "dashboard.py",
        auth=(username, password),
    )
    assert "Dashboard" in response.text
    assert not session.is_logged_in()
    assert session.get_auth_cookie() is None

    session = CMKWebSession(site)
    response = session.get(
        "dashboard.py",
        headers={
            "Authorization": f"Bearer {username} {password}",
        },
    )
    assert "Dashboard" in response.text
    assert not session.is_logged_in()
    assert session.get_auth_cookie() is None


@pytest.mark.skip_if_edition("saas")
def test_automation_user_rest_api(with_automation_user: tuple[str, str], site: Site) -> None:
    """test authenticated request of an automation user to the rest api

    - the HTTP param login must work in Checkmk 2.3
    - a session must not be established
    """
    username, password = with_automation_user

    session = CMKWebSession(site)
    response = session.get(
        f"/{site.id}/check_mk/api/1.0/version",
        auth=(username, password),
    )
    assert "site" in response.json()
    assert not session.is_logged_in()
    assert session.get_auth_cookie() is None

    session = CMKWebSession(site)
    response = session.get(
        f"/{site.id}/check_mk/api/1.0/version",
        headers={
            "Authorization": f"Bearer {username} {password}",
        },
    )
    assert "site" in response.json()
    assert not session.is_logged_in()
    assert session.get_auth_cookie() is None


@pytest.mark.skip_if_edition("saas")
def test_human_user_gui(site: Site) -> None:
    """test authenticated request of a "normal"/"human" user to the gui

    - the HTTP param login must not work
    - a session must be established
    """
    username = "cmkadmin"
    password = site.admin_password

    session = CMKWebSession(site)
    response = session.get(
        "dashboard.py",
        params={
            "_username": username,
            "_secret": password,
        },
        allow_redirect_to_login=True,
    )
    assert "Dashboard" not in response.text
    assert not session.is_logged_in()
    assert session.get_auth_cookie() is None

    session = CMKWebSession(site)
    response = session.get(
        "dashboard.py",
        auth=(username, password),
    )
    assert "Dashboard" in response.text
    assert session.is_logged_in()
    assert session.get_auth_cookie() is not None

    session = CMKWebSession(site)
    response = session.get(
        "dashboard.py",
        headers={
            "Authorization": f"Bearer {username} {password}",
        },
    )
    assert "Dashboard" in response.text
    assert session.is_logged_in()
    assert session.get_auth_cookie() is not None


@pytest.mark.skip_if_edition("saas")
def test_human_user_restapi(site: Site) -> None:
    """test authenticated request of a "normal"/"human" user to the rest api

    - the HTTP param login must not work
    - a session must not be established
    """

    username = "cmkadmin"
    password = site.admin_password

    session = CMKWebSession(site)
    response = session.get(
        f"/{site.id}/check_mk/api/1.0/version",
        params={
            "_username": username,
            "_secret": password,
        },
        expected_code=401,
    )
    assert not session.is_logged_in()
    assert session.get_auth_cookie() is None

    session = CMKWebSession(site)
    response = session.get(
        f"/{site.id}/check_mk/api/1.0/version",
        auth=(username, password),
    )
    assert "site" in response.json()
    assert not session.is_logged_in()
    assert session.get_auth_cookie() is None

    session = CMKWebSession(site)
    response = session.get(
        f"/{site.id}/check_mk/api/1.0/version",
        headers={
            "Authorization": f"Bearer {username} {password}",
        },
    )
    assert "site" in response.json()
    assert not session.is_logged_in()
    assert session.get_auth_cookie() is None


def _get_failed_logins(site: Site, user: str) -> int:
    return int(site.read_file(f"var/check_mk/web/{user}/num_failed_logins.mk"))


def _set_failed_logins(site: Site, user: str, value: int) -> None:
    site.write_file(f"var/check_mk/web/{user}/num_failed_logins.mk", f"{value}\n")


@contextlib.contextmanager
def _reset_failed_logins(site: Site, username: str) -> Iterator[None]:
    assert 0 == _get_failed_logins(site, username), "initially no failed logins"
    try:
        yield
    finally:
        _set_failed_logins(site, username, 0)


@pytest.mark.skip_if_edition("saas")
def test_failed_login_counter_human(site: Site) -> None:
    """test that all authentication methods count towards the failed login attempts"""
    session = CMKWebSession(site)

    with _reset_failed_logins(site, username := "cmkadmin"):
        session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            headers={"Authorization": f"Bearer {username} wrong_password"},
            expected_code=401,
        )
        assert 1 == _get_failed_logins(site, username), (
            "failed attempts increased by login with bearer token"
        )

        session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            auth=(username, "wrong_password"),
            expected_code=401,
        )
        assert 2 == _get_failed_logins(site, username), (
            "failed attempts increased by login with basic token"
        )

        session.post(
            "login.py",
            params={
                "_username": username,
                "_password": "wrong_password",
                "_login": "Login",
            },
            allow_redirect_to_login=True,
        )

        assert 3 == _get_failed_logins(site, username), (
            "failed attempts increased by login via login form"
        )


def test_failed_login_counter_automation(with_automation_user: tuple[str, str], site: Site) -> None:
    """test that the automation user does not get locked (see Werk #15198)"""
    session = CMKWebSession(site)

    username, _password = with_automation_user
    with _reset_failed_logins(site, username):
        session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            headers={"Authorization": f"Bearer {username} wrong_password"},
            expected_code=401,
        )
        assert 0 == _get_failed_logins(site, username)

        session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            auth=(username, "wrong_password"),
            expected_code=401,
        )
        assert 0 == _get_failed_logins(site, username)


@pytest.mark.skip_if_edition("saas")
def test_local_secret_no_sessions(site: Site) -> None:
    """test authenticated request with the site internal secret

    - a session must not be established
    """
    b64_token = site.get_site_internal_secret().b64_str
    session = CMKWebSession(site)
    response = session.get(
        f"/{site.id}/check_mk/api/1.0/version",
        headers={
            "Authorization": f"InternalToken {b64_token}",
        },
    )
    assert "site" in response.json()
    assert not session.is_logged_in()
    assert session.get_auth_cookie() is None

    session = CMKWebSession(site)
    response = session.get(
        "dashboard.py",
        headers={
            "Authorization": f"InternalToken {b64_token}",
        },
    )
    assert "Dashboard" in response.text
    assert not session.is_logged_in()
    assert session.get_auth_cookie() is None


def test_local_secret_permissions(site: Site) -> None:
    """test if all pages are accessible by the local_secret

    while introducing the secret and refactoring code to this secret we should
    add tests here to make sure the functionality works..."""

    session = CMKWebSession(site)
    b64_token = site.get_site_internal_secret().b64_str
    response = session.get(
        f"/{site.id}/check_mk/api/1.0/agent_controller_certificates_settings",
        headers={
            "Authorization": f"InternalToken {b64_token}",
        },
    )
    assert response.status_code == 200
    assert isinstance(response.json()["lifetime_in_months"], int)

    response = session.get(
        f"/{site.id}/check_mk/ajax_graph_images.py",
        headers={
            "Authorization": f"InternalToken {b64_token}",
        },
    )
    assert response.status_code == 200


@contextlib.contextmanager
def enable_2fa(site: Site, username: str) -> Iterator[None]:
    """enables totp as second factor for username

    Caution, this overrides any previous 2fa configs"""

    site.write_file(
        f"var/check_mk/web/{username}/two_factor_credentials.mk",
        repr(
            TwoFactorCredentials(
                webauthn_credentials={},
                backup_codes=[],
                totp_credentials={
                    "foo": TotpCredential(
                        credential_id="foo",
                        secret=b"\0",
                        version=1,
                        registered_at=0,
                        alias="alias",
                    )
                },
            )
        ),
    )
    try:
        yield
    finally:
        site.delete_file(f"var/check_mk/web/{username}/two_factor_credentials.mk")


def test_rest_api_access_with_enabled_2fa(site: Site) -> None:
    """you're not supposed to access the rest api if you have 2fa enabled (except for cookie auth)

    See: CMK-18988"""
    username = "cmkadmin"
    password = site.admin_password
    with enable_2fa(site, "cmkadmin"):
        session = CMKWebSession(site)
        response = session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            auth=(username, password),
            expected_code=401,
        )
        assert "site" not in response.json()
        assert not session.is_logged_in()


@pytest.mark.skip_if_edition("saas")
def test_rest_api_access_by_cookie_2fa(site: Site) -> None:
    """login via the gui but do not complete the 2fa, the cookie must not allow you access to the
    rest api

    See: CMK-18988"""

    username = "cmkadmin"
    password = site.admin_password

    with enable_2fa(site, "cmkadmin"):
        session = CMKWebSession(site)
        response = session.post(
            "login.py",
            data={
                "filled_in": "login",
                "_username": username,
                "_password": password,
                "_login": "Login",
            },
        )
        assert "Enter the six-digit code from your authenticator app to log in." in response.text

        response = session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            expected_code=401,
        )
        assert "site" not in response.json()
        assert not session.is_logged_in()


@pytest.mark.skip_if_edition("raw", "saas")
def test_invalid_remote_site_login(site: Site) -> None:
    """test that we are not logged in with any remote site secret

    AFAIK we have not configured a remote site at that point so no secret should work.
    In the raw edition we don't have the `register_agent.py` page since the agent
    bakery is a enterprise feature."""

    session = CMKWebSession(site)
    response = session.get(
        f"/{site.id}/check_mk/register_agent.py",
        headers={
            "Authorization": f"RemoteSite {base64.b64encode(b'foobar').decode()}",
        },
        allow_redirect_to_login=True,
    )
    assert "check_mk/login.py" in response.url
