#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import base64
import binascii
import hmac
import traceback
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Callable

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
from cmk.gui.userdb.session import auth_cookie_name, generate_auth_hash
from cmk.gui.utils.urls import requested_file_name

auth_logger = logger.getChild("auth")

AuthFunction = Callable[[], UserId | None]


def _check_auth() -> tuple[UserId, AuthType]:
    # NOTE: To push this list into the global namespace, the ordering of the methods need to
    #       be taken into account.
    auth_methods: list[tuple[AuthFunction, AuthType]] = [
        # Automation authentication via _username and _secret overrules everything else.
        (check_auth_by_cookie, "cookie"),
        (check_auth_by_custom_http_header, "http_header"),
        (check_auth_by_remote_user, "web_server"),
        (check_auth_by_basic_header, "web_server"),
        (check_auth_by_bearer_header, "bearer"),
        # Automation authentication via _username and _secret overrules everything else.
        (check_auth_by_automation_credentials_in_request_values, "automation"),
    ]
    candidates: list[tuple[UserId, AuthType]] = []
    for auth_method, auth_type in auth_methods:
        user_id = auth_method()
        # NOTE: It's important for these methods to always raise an exception whenever something
        # strange is happening. This will abort the whole process, regardless of which auth method
        # succeeded or not.
        if user_id:
            candidates.append((user_id, auth_type))

    if not candidates:
        raise MKAuthException("Couldn't log in.")

    # We take the last one, which is the most specific one.
    user_id, auth_type = candidates[-1]
    return _check_user(user_id), auth_type


def _check_user(user_id: UserId) -> UserId:
    if not active_config.user_login and not is_site_login():
        raise MKAuthException("Site can't be logged into.")

    # NOTE
    # These are meant to be safeguards for programming errors which wouldn't be caught
    # by our linters and type-checkers. So leave them in place, even though the type
    # says user_id can only ever be a UserId.
    if not user_id:
        raise MKAuthException("User can't log in.")

    if not isinstance(user_id, str):
        raise MKInternalError(_("Invalid user authentication"))

    if not userdb.is_customer_user_allowed_to_login(user_id):
        # A CME not assigned with the current sites customer
        # is not allowed to log in
        auth_logger.debug("User '%s' is not allowed to authenticate: Invalid customer" % user_id)
        raise MKAuthException("Unknown customer. Can't log in.")

    return user_id


def _try_user_id(user_id: str) -> UserId:
    """Try wrapping a UserId, but throw an HTTPAuthException when impossible."""
    if not user_id:
        raise MKAuthException("Empty user not allowed.")
    try:
        return UserId(user_id)
    except ValueError as exc:
        raise MKAuthException("Illegal username.") from exc


def check_auth_by_basic_header() -> UserId | None:
    """Authenticate the user via the HTTP_AUTHORIZATION header
    Returns:
        A UserId if authenticated successfully

    Raises:
        MKAuthError:
            - when the user in REMOTE_USER is different to the one in HTTP_AUTHORIZATION
    """
    if auth_header := request.environ.get("HTTP_AUTHORIZATION", ""):
        if auth_header.startswith("Basic "):
            user_id, _secret = user_from_basic_header(auth_header)
            if not verify_credentials(user_id, _secret):
                raise MKAuthException("Wrong credentials (Basic header)")
            # Even if the credentials verify that the user may log in, if these don't match, we
            # abort anyway, because this doesn't make any sense.
            if remote_user := check_auth_by_remote_user():
                if user_id and user_id != remote_user:
                    raise MKAuthException("Mismatch in authentication headers.")
            return user_id

    return None


def check_auth_by_bearer_header() -> UserId | None:
    """Authenticate the user via the HTTP_AUTHORIZATION header
    Returns:
        None - if not authenticated
        A tuple of UserId and AuthType if authenticated successfully
    Raises:
        MKAuthError:
            - when the user in REMOTE_USER is different to the one in HTTP_AUTHORIZATION
    """
    if auth_header := request.environ.get("HTTP_AUTHORIZATION", ""):
        try:
            auth_type, _ = auth_header.split(None, 1)
        except ValueError:
            return None

        if auth_type == "Bearer":
            user_id, secret = user_from_bearer_header(auth_header)
            if not verify_credentials(user_id, secret):
                raise MKAuthException("Wrong credentials (Bearer header)")

            return user_id

    return None


def verify_credentials(user_id: UserId, password: Password) -> bool:
    if verify_automation_secret(user_id, password.raw):
        return True
    if verify_gui_secret(user_id, password, datetime.now()):
        return True
    return False


def user_from_basic_header(auth_header: str) -> tuple[UserId, Password]:
    """Decode a Basic Authorization header

    Examples:
        >>> user_from_basic_header("Basic Zm9vYmF6YmFyOmZvb2JhemJhcg==")  # doctest: +ELLIPSIS
        ('foobazbar', <cmk.utils.crypto...>)

        >>> import pytest
        >>> with pytest.raises(MKAuthException):
        ...     user_from_basic_header("Basic SGFsbG8gV2VsdCE=")  # 'Hallo Welt!'

        >>> with pytest.raises(MKAuthException):
        ...     user_from_basic_header("Basic foobazbar")

        >>> with pytest.raises(MKAuthException):
        ...      user_from_basic_header("Basic     ")

    Args:
        auth_header:
            The content of the HTTP_AUTHORIZATION header as a string.

    Returns:
        A tuple of UserId and password.

    """
    try:
        _, token = auth_header.split("Basic ", 1)
    except ValueError as exc:
        raise MKAuthException("Not a valid Basic token.") from exc
    if not token.strip():
        raise MKAuthException("Not a valid Basic token.")

    try:
        user_entry = base64.b64decode(token.strip()).decode("utf8")
    except binascii.Error as exc:
        raise MKAuthException("Not a valid Basic token.") from exc
    except UnicodeDecodeError as exc:
        raise MKAuthException("Not a valid Basic token.") from exc

    try:
        user_id, secret = user_entry.split(":", 1)
    except ValueError as exc:
        raise MKAuthException("Not a valid Basic token.") from exc

    return _try_user_id(user_id), Password(secret)


def verify_automation_secret(user_id: UserId, secret: str) -> bool:
    if secret and user_id and "/" not in user_id:
        path = Path(cmk.utils.paths.var_dir) / "web" / user_id / "automation.secret"
        if not path.is_file():
            return False

        with path.open(encoding="utf-8") as f:
            return f.read().strip() == secret

    return False


def check_auth_by_custom_http_header() -> UserId | None:
    """When http header auth is enabled, try to read the user_id from the var"""
    if auth_by_http_header := active_config.auth_by_http_header:
        if not (user_name := request.headers.get(auth_by_http_header, type=str)):
            return None

        return _try_user_id(user_name)

    return None


def check_auth_by_remote_user() -> UserId | None:
    """Try to get the authenticated user from the HTTP request

    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user.
    """
    # ? type of Request.remote_user attribute is unclear
    user_name = request.remote_user
    if user_name is None:
        return None

    user_id = _try_user_id(user_name)
    if userdb.user_exists(user_id):
        return user_id

    raise MKAuthException(f"User {user_id} does not exist.")


def check_auth_by_automation_credentials_in_request_values() -> UserId | None:
    """Check credentials either in query string or form encoded POST body

    Raises:
        MKAuthException: whenever an illegal username is detected.
    """
    user_name = request.values.get("_username")
    password = request.values.get("_secret")
    if user_name is not None and password is not None:
        user_id = _try_user_id(user_name)
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
        # Why and how does this happen and why we can't do it another way.
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


def user_from_bearer_header(auth_header: str) -> tuple[UserId, Password]:
    """Authenticate a user from username and password sent in the header.

    Examples:

        >>> username, password = user_from_bearer_header("Bearer username password")
        >>> (username, password.raw)
        ('username', 'password')

    Args:
        auth_header:
            The content of the HTTP_AUTHORIZATION header as a string.

    Returns:
        A tuple of UserId and password.

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

    return _try_user_id(user_id), Password(secret)


def verify_gui_secret(user_id: UserId | None, secret: Password, now: datetime) -> bool:
    """Verify a GUI secret.

    Returns:
        True if the User is a valid GUI user, False otherwise.

    Raises:
        Nothing

    """
    if user_id is None:
        return False

    try:
        return bool(userdb.check_credentials(user_id, secret, now))
    except MKUserError:
        return False
