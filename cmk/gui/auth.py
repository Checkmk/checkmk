#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import hmac
import time
import traceback
from contextlib import suppress
from datetime import datetime
from pathlib import Path

import cmk.utils
import cmk.utils.paths
from cmk.utils.crypto.password import Password
from cmk.utils.type_defs import UserId

from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKInternalError, MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.type_defs import AuthType
from cmk.gui.userdb.session import auth_cookie_name, generate_auth_hash, on_succeeded_login
from cmk.gui.utils.urls import requested_file_name
from cmk.gui.wsgi.type_defs import RFC7662


def _check_auth() -> tuple[UserId, AuthType]:
    if user_id := _check_auth_web_server():
        return _check_user(user_id, "web_server")

    if user_id := check_automation_auth_by_request_values():
        return _check_user(user_id, "automation")

    if user_id := _check_auth_http_header():
        return _check_user(user_id, "http_header")

    if user_id := check_auth_by_cookie():
        return _check_user(user_id, "cookie")

    raise MKAuthException("Couldn't log in.")


def _check_user(user_id: UserId | None, auth_type: AuthType) -> tuple[UserId, AuthType]:
    if not active_config.user_login:
        raise MKAuthException("Site can't be logged into.")

    if (user_id is not None and not isinstance(user_id, str)) or user_id == "":
        raise MKInternalError(_("Invalid user authentication"))

    if user_id and not userdb.is_customer_user_allowed_to_login(user_id):
        # A CME not assigned with the current sites customer
        # is not allowed to log in
        auth_logger.debug("User '%s' is not allowed to authenticate: Invalid customer" % user_id)
        raise MKAuthException("Unknown customer. Can't log in.")

    if user_id and auth_type in ("http_header", "web_server"):
        if auth_cookie_name() not in request.cookies:
            on_succeeded_login(user_id, datetime.now())

    if not active_config.user_login and not is_site_login():
        raise MKAuthException("Site can't be logged into.")

    if user_id is None:
        raise MKAuthException("User can't log in.")

    return user_id, auth_type


def verify_automation_secret(user_id: UserId, secret: str) -> bool:
    if secret and user_id and "/" not in user_id:
        path = Path(cmk.utils.paths.var_dir) / "web" / user_id / "automation.secret"
        if not path.is_file():
            return False

        with path.open(encoding="utf-8") as f:
            return f.read().strip() == secret

    return False


def _check_auth_automation() -> UserId:
    secret = request.get_str_input_mandatory("_secret", "").strip()
    user_id = request.get_validated_type_input_mandatory(UserId, "_username", UserId.builtin())

    request.del_var_from_env("_username")
    request.del_var_from_env("_secret")

    if verify_automation_secret(user_id, secret):
        return user_id
    raise MKAuthException(_("Invalid automation secret for user %s") % user_id)


def _check_auth_http_header() -> UserId | None:
    """When http header auth is enabled, try to read the user_id from the var"""
    user_id = None

    if auth_by_http_header := active_config.auth_by_http_header:
        user_id = request.headers.get(auth_by_http_header, type=str)

    if not user_id:
        return None

    return UserId(user_id)


def _check_auth_web_server() -> UserId | None:
    """Try to get the authenticated user from the HTTP request

    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user.
    """
    # ? type of Request.remote_user attribute is unclear
    user_id = request.remote_user
    if user_id is None:
        return None

    return UserId(user_id)


def check_automation_auth_by_request_values() -> UserId | None:
    """Check credentials either in query string or form encoded POST body"""
    user_name = request.values.get("_username")
    password = request.values.get("_secret")
    if user_name is not None and password is not None:
        user_id = UserId(user_name)
        if verify_automation_secret(user_id, password):
            return user_id

    return None


def check_auth_by_cookie() -> UserId | None:
    """check if session cookie exists and if it is valid

    Returns None if not authenticated. If a user was successfully authenticated,
    the UserId is returned
    """

    cookie_name = auth_cookie_name()
    if cookie_name not in request.cookies:
        return None

    try:
        username, session_id, cookie_hash = user_from_cookie(_fetch_cookie(cookie_name))
        check_parsed_auth_cookie(username, session_id, cookie_hash)
        userdb.on_access(username, session_id, datetime.now())
        return username
    except MKAuthException:
        # Suppress cookie validation errors from other sites cookies
        auth_logger.debug(
            f"Exception while checking cookie {cookie_name}: {traceback.format_exc()}"
        )

    return None


def is_site_login() -> bool:
    """Determine if login is a site login for connecting central and remote
    site. This login has to be allowed even if site login on remote site is not
    permitted by rule "Direct login to Web GUI allowed" """
    if requested_file_name(request) == "login":
        if (origtarget_var := request.var("_origtarget")) is None:
            return False
        return (
            origtarget_var.startswith("automation_login.py")
            and "_version=" in origtarget_var
            and "_edition_short=" in origtarget_var
        )

    if requested_file_name(request) == "automation_login":
        return bool(request.var("_edition_short") and request.var("_version"))

    return False


auth_logger = logger.getChild("auth")


def user_from_cookie(raw_cookie: str) -> tuple[UserId, str, str]:
    """

    Raises:
        - MKAuthException: when the cookie is malformed
        - MKAuthException: when the session_id is of an old format
    """
    try:
        username, session_id, cookie_hash = raw_cookie.split(":", 2)
        # Careful. Instantiating UserId may raise as well.
        user_id = UserId(username)
    except ValueError:
        raise MKAuthException("Invalid auth cookie.")

    # Refuse pre 2.0 cookies: These held the "issue time" in the 2nd field.
    with suppress(ValueError):
        float(session_id)
        raise MKAuthException("Refusing pre 2.0 auth cookie")

    return user_id, session_id, cookie_hash


def _fetch_cookie(cookie_name: str) -> str:
    raw_cookie = request.cookies.get(cookie_name, default="::", type=str)
    assert raw_cookie is not None
    return raw_cookie


def check_parsed_auth_cookie(username: UserId, session_id: str, cookie_hash: str) -> None:
    if not userdb.user_exists(username):
        raise MKAuthException(_("Username is unknown"))

    if not hmac.compare_digest(cookie_hash, generate_auth_hash(username, session_id)):
        raise MKAuthException(_("Invalid credentials"))


def user_from_bearer_header(auth_header: str) -> tuple[UserId, Password[str]]:
    """

    Examples:

        >>> username, password = user_from_bearer_header("Bearer username password")
        >>> (username, password.raw)
        ('username', 'password')

    Args:
        auth_header:

    Returns:

    """
    try:
        _, token = auth_header.split("Bearer ", 1)
    except ValueError:
        raise MKAuthException(f"Not a valid Bearer token: {auth_header}")
    try:
        user_id, secret = token.strip().split(" ", 1)
    except ValueError:
        raise MKAuthException("No user/password combination in Bearer token.")
    if not secret:
        raise MKAuthException("Empty password not allowed.")
    if not user_id:
        raise MKAuthException("Empty user not allowed.")
    if "/" in user_id:
        raise MKAuthException("No slashes / allowed in username.")

    return UserId(user_id), Password(secret)


def automation_auth(user_id: UserId, secret: Password[str]) -> RFC7662 | None:
    if verify_automation_secret(user_id, secret.raw):
        return rfc7662_subject(user_id, "bearer")

    return None


def gui_user_auth(user_id: UserId, secret: Password[str], now: datetime) -> RFC7662 | None:
    try:
        if userdb.check_credentials(user_id, secret, now):
            return rfc7662_subject(user_id, "bearer")
    except MKUserError:
        # This is the case of "Automation user rejected". We don't care about that in the REST API
        # because every type of user is allowed in.
        return None

    return None


def rfc7662_subject(user_id: UserId, _auth_type: AuthType) -> RFC7662:
    """Create a RFC7662 compatible user representation

    Args:
        user_id:
            The user's user_id

        _auth_type:
            One of 'automation', 'cookie', 'web_server', 'http_header', 'bearer'

    Returns:
        The filled-out dictionary.
    """
    return {"sub": user_id, "iat": int(time.time()), "active": True, "scope": _auth_type}
