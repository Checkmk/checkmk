#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import contextlib
from ast import literal_eval
from collections.abc import Callable, Iterator
from datetime import datetime

import pytest

from cmk.ccc.user import UserId
from cmk.crypto.totp import TOTP
from cmk.gui.type_defs import TotpCredential, TwoFactorCredentials
from cmk.gui.userdb.session import generate_auth_hash
from tests.testlib.site import ADMIN_USER, Site
from tests.testlib.web_session import CMKWebSession


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


@pytest.mark.skip_if_edition("cloud")
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


@pytest.mark.skip_if_edition("cloud")
def test_session_cookie(site: Site) -> None:
    web = CMKWebSession(site)
    web.login()

    cookie = web.get_auth_cookie()

    assert cookie is not None
    assert cookie.path == f"/{site.id}/"
    # This is ugly but IMHO the only way...
    assert "HttpOnly" in cookie.__dict__.get("_rest", {})
    assert cookie.__dict__.get("_rest", {}).get("SameSite") == "Lax"


@pytest.mark.skip_if_edition("cloud")
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
    assert "cmk-dashboard" in response.text
    assert not session.is_logged_in()

    session = CMKWebSession(site)
    response = session.get(
        "dashboard.py",
        headers={
            "Authorization": f"Bearer {username} {password}",
        },
    )
    assert "cmk-dashboard" in response.text
    assert not session.is_logged_in()


@pytest.mark.skip_if_edition("cloud")
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

    session = CMKWebSession(site)
    response = session.get(
        f"/{site.id}/check_mk/api/1.0/version",
        headers={
            "Authorization": f"Bearer {username} {password}",
        },
    )
    assert "site" in response.json()
    assert not session.is_logged_in()


@pytest.mark.skip_if_edition("cloud")
def test_human_user_gui(site: Site) -> None:
    """test authenticated request of a "normal"/"human" user to the gui

    - the HTTP param login must not work
    - a session must be established
    """
    username = ADMIN_USER
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
    assert "cmk-dashboard" not in response.text
    assert not session.is_logged_in()

    session = CMKWebSession(site)
    response = session.get(
        "dashboard.py",
        auth=(username, password),
    )
    assert "cmk-dashboard" in response.text
    assert session.is_logged_in()

    session = CMKWebSession(site)
    response = session.get(
        "dashboard.py",
        headers={
            "Authorization": f"Bearer {username} {password}",
        },
    )
    assert "cmk-dashboard" in response.text
    assert session.is_logged_in()


@pytest.mark.skip_if_edition("cloud")
def test_human_user_restapi(site: Site) -> None:
    """test authenticated request of a "normal"/"human" user to the rest api

    - the HTTP param login must not work
    - a session must not be established
    """

    username = ADMIN_USER
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

    session = CMKWebSession(site)
    response = session.get(
        f"/{site.id}/check_mk/api/1.0/version",
        auth=(username, password),
    )
    assert "site" in response.json()
    assert not session.is_logged_in()

    session = CMKWebSession(site)
    response = session.get(
        f"/{site.id}/check_mk/api/1.0/version",
        headers={
            "Authorization": f"Bearer {username} {password}",
        },
    )
    assert "site" in response.json()
    assert not session.is_logged_in()


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


@pytest.mark.skip_if_edition("cloud")
def test_failed_login_counter_human(site: Site) -> None:
    """test that all authentication methods count towards the failed login attempts"""
    session = CMKWebSession(site)

    with _reset_failed_logins(site, username := ADMIN_USER):
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


@pytest.mark.skip_if_edition("cloud")
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

    session = CMKWebSession(site)
    response = session.get(
        "dashboard.py",
        headers={
            "Authorization": f"InternalToken {b64_token}",
        },
    )
    assert "cmk-dashboard" in response.text
    assert not session.is_logged_in()


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


@contextlib.contextmanager
def require_password_change(site: Site, username: str) -> Iterator[None]:
    """Requires password change for username; unconditionally unsets the flag on exit!"""
    pw_change_marker = f"var/check_mk/web/{username}/enforce_pw_change.mk"

    site.write_file(pw_change_marker, "1\n")
    try:
        yield
    finally:
        site.delete_file(pw_change_marker)


@contextlib.contextmanager
def update_global_config(site: Site, new_config: list[str]) -> Iterator[None]:
    """Multiple auth settings require the global config to be updated. Config reset on exit"""
    global_config_path = "etc/check_mk/multisite.d/wato/global.mk"
    backup = site.read_file(global_config_path)
    site.write_file(global_config_path, backup + "\n".join(new_config))
    try:
        yield
    finally:
        site.write_file(global_config_path, backup)


@pytest.mark.parametrize(
    "additional_auth_config, kwargs, expected_error_msg",
    [
        pytest.param(
            enable_2fa,
            {"username": ADMIN_USER},
            "Two-factor authentication is required.",
            id="2fa_auth_required",
        ),
        pytest.param(
            require_password_change,
            {"username": ADMIN_USER},
            "Password change is required.",
            id="password_change_required",
        ),
        pytest.param(
            update_global_config,
            {"new_config": ["require_two_factor_all_users = True"]},
            "Two-factor setup is required for user.",
            id="2fa_setup_required",
        ),
    ],
)
def test_rest_api_basic_auth_denied_by_auth_config(  # type: ignore[misc] #mypy struggles to evaluate additional_auth_config methods
    site: Site,
    additional_auth_config: Callable[..., contextlib.AbstractContextManager[None]],
    kwargs: dict[str, str],
    expected_error_msg: str,
) -> None:
    """If an account has any additional action required such as 2fa or password change, the user must be denied."""
    password = site.admin_password
    session = CMKWebSession(site)
    with additional_auth_config(site, **kwargs):
        response = session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            auth=(ADMIN_USER, password),
            expected_code=401,
        )
        assert not session.is_logged_in()
        assert response.json()["detail"] == expected_error_msg


@pytest.mark.parametrize(
    "additional_auth_config, kwargs, expected_error_msg",
    [
        pytest.param(
            enable_2fa,
            {"username": ADMIN_USER},
            "Two-factor authentication is required.",
            id="2fa_auth_required",
        ),
        pytest.param(
            require_password_change,
            {"username": ADMIN_USER},
            "Password change is required.",
            id="password_change_required",
        ),
        pytest.param(
            update_global_config,
            {"new_config": ["require_two_factor_all_users = True"]},
            "Two-factor setup is required for user.",
            id="2fa_setup_required",
        ),
    ],
)
def test_rest_api_bearer_auth_denied_by_auth_config(  # type: ignore[misc]
    site: Site,
    additional_auth_config: Callable[..., contextlib.AbstractContextManager[None]],
    kwargs: dict[str, str],
    expected_error_msg: str,
) -> None:
    """If an account has any additional action required such as 2fa or password change, the user must be denied"""
    session = CMKWebSession(site)
    with additional_auth_config(site, **kwargs):
        response = session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            headers={
                "Authorization": f"Bearer {ADMIN_USER} {site.admin_password}",
            },
            expected_code=401,
        )
        assert not session.is_logged_in()
        assert response.json()["detail"] == expected_error_msg


@pytest.mark.parametrize(
    "additional_auth_config, global_edits, user",
    [
        pytest.param(
            enable_2fa,
            ["auth_by_http_header = 'X-Remote-User'"],
            ADMIN_USER,
            id="2fa_auth_required_valid_user",
        ),
        pytest.param(
            require_password_change,
            ["auth_by_http_header = 'X-Remote-User'"],
            ADMIN_USER,
            id="password_change_required_valid_user",
        ),
        pytest.param(
            lambda *args: contextlib.nullcontext(),
            ["require_two_factor_all_users = True", "auth_by_http_header = 'X-Remote-User'"],
            ADMIN_USER,
            id="2fa_setup_required_valid_user",
        ),
    ],
)
def test_remote_user_denied_by_additional_auth_configs(  # type: ignore[misc]
    site: Site,
    additional_auth_config: Callable[..., contextlib.AbstractContextManager[None]],
    global_edits: list[str],
    user: str,
) -> None:
    """This test sets a custom header/remote user in the global config, then ensures that all secondary
    auth methods appropriately deny access."""
    session = CMKWebSession(site)
    with (
        additional_auth_config(site, ADMIN_USER),
        update_global_config(site, global_edits),
    ):
        session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            headers={
                "X-Remote-User": user,
            },
            expected_code=401,
        )
        assert not session.is_logged_in()


@pytest.mark.parametrize(
    "additional_auth_config, global_edits, user, expected_error_msg, expected_code",
    [
        pytest.param(
            enable_2fa,
            ["auth_by_http_header = 'X-Remote-User'"],
            "fake_user",
            "Two-factor authentication is required.",
            200,
            id="2fa_auth_required_invalid_user",
        ),
        pytest.param(
            require_password_change,
            ["auth_by_http_header = 'X-Remote-User'"],
            "fake_user",
            "Password change is required.",
            200,
            id="password_change_required_invalid_user",
        ),
        pytest.param(
            lambda *args: contextlib.nullcontext(),
            ["require_two_factor_all_users = True", "auth_by_http_header = 'X-Remote-User'"],
            "fake_user",
            "Two-factor setup is required for user.",
            401,
            id="2fa_setup_required_invalid_user",
        ),
    ],
)
def test_invalid_remote_user_not_denied_by_additional_auth_configs(  # type: ignore[misc]
    site: Site,
    additional_auth_config: Callable[..., contextlib.AbstractContextManager[None]],
    global_edits: list[str],
    user: str,
    expected_error_msg: str,
    expected_code: int,
) -> None:
    """This test sets a custom header/remote user in the global config.
    Two-factor authentication needed and password change required, should not block this authentication header
    for fake/unknown users.
    Enforce two factor (noted as setup) is intended to always block both real and fake users."""
    session = CMKWebSession(site)
    with (
        additional_auth_config(site, ADMIN_USER),
        update_global_config(site, global_edits),
    ):
        response = session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            headers={
                "X-Remote-User": user,
            },
            expected_code=expected_code,
        )
        assert not session.is_logged_in()
        if response.status_code == 401:
            assert response.json()["detail"] == expected_error_msg


def _get_site_auth_cookie(site: Site, username: str) -> dict[str, str]:
    """Access session_info information and craft user's latest auth cookie"""
    session_info_mk = literal_eval(site.read_file(f"var/check_mk/web/{username}/session_info.mk"))
    session_id = next(iter(session_info_mk))
    cookie_value = str(
        username + ":" + session_id + ":" + generate_auth_hash(UserId(username), session_id)
    )
    cookie_name = "auth_" + site.id
    return {cookie_name: cookie_value}


@pytest.mark.skip_if_edition("cloud")
def test_rest_api_access_allowed_by_cookie_without_2fa(site: Site) -> None:
    """login via the gui and get a valid cookie, cookie should work when no 2fa."""

    username = ADMIN_USER
    password = site.admin_password
    session = CMKWebSession(site)

    # Login to GUI
    session.post(
        "login.py",
        data={
            "filled_in": "login",
            "_username": username,
            "_password": password,
            "_login": "Login",
        },
    )

    # Use cookie for RestAPI
    session.get(
        f"/{site.id}/check_mk/api/1.0/version",
        cookies=_get_site_auth_cookie(site, username),
        expected_code=200,
    )
    assert session.is_logged_in()


@pytest.mark.skip_if_edition("cloud")
def test_rest_api_access_denied_by_cookie_without_2fa(site: Site) -> None:
    """login via the gui but do not complete the 2fa, the cookie must not allow you access to the
    rest api"""

    username = ADMIN_USER
    password = site.admin_password

    with enable_2fa(site, username):
        session = CMKWebSession(site)

        # Login to GUI
        session.post(
            "login.py",
            data={
                "filled_in": "login",
                "_username": username,
                "_password": password,
                "_login": "Login",
            },
        )

        # Use cookie for RestAPI
        response = session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            cookies=_get_site_auth_cookie(site, username),
            expected_code=401,
        )
        assert response.json()["detail"] == "Two-factor authentication is required."


@pytest.mark.skip_if_edition("cloud")
def test_rest_api_access_allowed_by_cookie_2fa(site: Site) -> None:
    """login via the gui and complete the 2fa, the cookie must not allow you access to the
    rest api"""
    username = ADMIN_USER

    with enable_2fa(site, ADMIN_USER):
        session = CMKWebSession(site)

        # Login
        session.post(
            "login.py",
            data={
                "filled_in": "login",
                "_username": username,
                "_password": site.admin_password,
                "_login": "Login",
            },
            allow_redirects=True,
        )

        # Generate valid TOTP code
        two_factor_file_contents = literal_eval(
            site.read_file(f"var/check_mk/web/{username}/two_factor_credentials.mk")
        )
        totp_uuid = list(two_factor_file_contents["totp_credentials"].keys())[0]

        authenticator = TOTP(two_factor_file_contents["totp_credentials"][totp_uuid]["secret"])
        current_time = authenticator.calculate_generation(datetime.now())
        otp_value = authenticator.generate_totp(current_time)

        # Perform GUI 2fa authentication
        session.post(
            "user_login_two_factor.py",
            data={
                "filled_in": "totp",
                "_totp_code": otp_value,
            },
            allow_redirects=True,
            expected_code=200,
        )

        # Generated cookie for latest user session should now work.
        session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            cookies=_get_site_auth_cookie(site, username),
            expected_code=200,
        )
        assert session.is_logged_in()


@pytest.mark.skip_if_edition("community", "cloud")
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
