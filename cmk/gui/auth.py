#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import base64
import binascii
import contextlib
import hmac
import re
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Literal

from cmk.ccc.user import UserId

import cmk.utils.paths
from cmk.utils.local_secrets import SiteInternalSecret
from cmk.utils.log.security_event import log_security_event

from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.pseudo_users import PseudoUserId, RemoteSitePseudoUser, SiteInternalPseudoUser
from cmk.gui.site_config import enabled_sites
from cmk.gui.type_defs import AuthType
from cmk.gui.userdb.session import generate_auth_hash
from cmk.gui.utils.htpasswd import Htpasswd
from cmk.gui.utils.security_log_events import AuthenticationFailureEvent
from cmk.gui.utils.urls import requested_file_name

from cmk.crypto import password_hashing
from cmk.crypto.password import Password
from cmk.crypto.secrets import Secret

auth_logger = logger.getChild("auth")


AuthFunction = Callable[[], UserId | PseudoUserId | None]


def check_auth() -> tuple[UserId | PseudoUserId, AuthType]:
    """Try to authenticate a user from the current request.

    This will attempt to authenticate the user via all possible authentication types.
    If any of them succeeds, the user's ID and the succeeding authentication type are returned.
    Some attempted authentication types may raise exceptions and abort this function preemptively.
    """
    if not active_config.user_login and not is_site_login():
        raise MKAuthException("Site can't be logged into.")

    auth_methods: list[tuple[AuthFunction, AuthType]] = [
        # NOTE: This list is sorted from the more general to the most specific auth methods.
        #       The most specific to succeed will be used in the end.
        (_check_auth_by_custom_http_header, "http_header"),
        (_check_auth_by_remote_user, "web_server"),
        (_check_auth_by_basic_header, "basic_auth"),
        (_check_auth_by_bearer_header, "bearer"),
        (_check_internal_token, "internal_token"),
        (_check_remote_site, "remote_site"),
    ]

    selected: tuple[UserId | PseudoUserId, AuthType] | None = None
    user_id = None
    for auth_method, auth_type in auth_methods:
        # NOTE: It's important for these methods to always raise an exception whenever something
        # strange is happening. This will abort the whole process, regardless of which auth method
        # succeeded or not.
        try:
            if user_id := auth_method():
                # The last auth_method is the most specific one, use that.
                selected = (user_id, auth_type)
        except Exception as e:
            log_security_event(
                AuthenticationFailureEvent(
                    user_error=str(e),
                    auth_method=auth_type,
                    username=user_id if isinstance(user_id, UserId) else None,
                    remote_ip=request.remote_ip,
                )
            )
            raise

    if not selected:
        raise MKAuthException("Couldn't log in.")

    if not isinstance(selected[0], PseudoUserId):
        _check_cme_login(selected[0])

    return selected


def is_site_login() -> bool:
    """Determine if login is a site login for connecting central and remote
    site. This login has to be allowed even if site login on remote site is not
    permitted by rule "Direct login to web GUI allowed".  This also applies to
    all rest-api requests, they should also be allowed in this scenario otherwise
    the agent-receiver won't work."""

    if re.match("/[^/]+/check_mk/api/", request.path) is not None:
        return True

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


def parse_and_check_cookie(raw_cookie: str) -> tuple[UserId, str, str]:
    """Parse the cookie string and validate it

    Returns:
        A tuple of the user ID, the session ID, and the cookie hash.

    Raises:
        MKAuthException: when the cookie is malformed
        MKAuthException: when the user ID is invalid or is not known
        MKAuthException: when the session ID is invalid or in pre 2.0 format
        MKAuthException: when the cookie's auth hash is invalid
    """
    try:
        username, session_id, cookie_hash = raw_cookie.split(":", 2)
    except ValueError:
        raise MKAuthException("Invalid auth cookie")

    user_id = _try_user_id(username)

    # Ensure the session ID is a proper UUID and not, for example, the float
    # value "issue time" that was stored in the 2nd field pre 2.0.
    # TODO: make session ID a real type with validation throughout the code
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise MKAuthException("Invalid session ID in auth cookie")

    if not userdb.user_exists(user_id):
        raise MKAuthException(_("Username is unknown"))

    if not hmac.compare_digest(cookie_hash, generate_auth_hash(user_id, session_id)):
        raise MKAuthException(_("Invalid credentials"))

    return user_id, session_id, cookie_hash


def _check_auth_by_custom_http_header() -> UserId | None:
    """When http header auth is enabled, try to read the user_id from the var

    WARNING: This way of authentication does NOT verify any credentials!
    """
    if (auth_by_http_header := active_config.auth_by_http_header) and (
        username := request.headers.get(auth_by_http_header, type=str)
    ):
        return _try_user_id(username)

    return None


def _check_auth_by_remote_user() -> UserId | None:
    """Try to get the authenticated user from the HTTP request

    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user.

    WARNING: This way of authentication does NOT verify any credentials!
    """
    if (username := request.remote_user) is None:
        return None

    user_id = _try_user_id(username)
    if userdb.user_exists(user_id):
        return user_id

    raise MKAuthException(f"User {user_id} does not exist.")


def _check_auth_by_header(
    token_name: Literal["Basic", "Bearer"], parse_token: Callable[[str], tuple[str, str]]
) -> UserId | None:
    """Parse the auth header and verify the credentials"""
    if not (
        (auth_header := request.environ.get("HTTP_AUTHORIZATION", ""))
        and auth_header.startswith(f"{token_name} ")
    ):
        return None

    try:
        username, passwd = parse_token(auth_header.split(f"{token_name} ")[1])
    except ValueError:
        raise MKAuthException(f"Invalid {token_name} token")

    user_id = _try_user_id(username)
    try:
        password = Password(passwd)
    except ValueError as e:
        # Note: not wrong, invalid. E.g. contains null bytes or is empty
        raise MKAuthException(f"Invalid password: {e}")

    # Could be an automation user or a regular user
    if _verify_automation_login(user_id, password.raw) or _verify_user_login(user_id, password):
        return user_id

    # At this point: invalid credentials. Could be user, password or both.
    # on_failed_login wants to be informed about non-existing users as well.
    userdb.on_failed_login(user_id, datetime.now())

    raise MKAuthException(f"Wrong credentials ({token_name} header)")


def _check_auth_by_basic_header() -> UserId | None:
    """Authenticate the user via Basic Auth token in the HTTP_AUTHORIZATION header

    Returns:
        a UserId if authenticated successfully
        None if no matching header is found

    Raises:
        MKAuthException: when the header is found but the credentials are not valid
        MKAuthException: when the user in REMOTE_USER is different to the one in HTTP_AUTHORIZATION
    """
    if not (user_id := _check_auth_by_header("Basic", _parse_basic_auth_token)):
        return None

    # Even if the credentials verify that the user may log in, if these don't match, we
    # abort anyway, because this doesn't make any sense.
    if (remote_user := _check_auth_by_remote_user()) and user_id != remote_user:
        raise MKAuthException("Mismatch in authentication headers.")

    return user_id


def _parse_basic_auth_token(token: str) -> tuple[str, str]:
    """Read username and password from a base64 encoded Basic Auth token.

    Examples:

        >>> _parse_basic_auth_token("Zm9vYmF6YmFyOmZvb2JhemJhcg==")
        ('foobazbar', 'foobazbar')

        _parse_basic_auth_token("SGFsbG8gV2VsdCE=")  # 'Hallo Welt!'
        Traceback (most recent call last):
        ...
        ValueError: ...

        _parse_basic_auth_token("foobazbar")
        Traceback (most recent call last):
        ...
        ValueError: ...

        _parse_basic_auth_token("    ")
        Traceback (most recent call last):
        ...
        ValueError: ...
    """
    user_id, password = base64.b64decode(token.strip()).decode("utf8").split(":", 1)
    return user_id, password


def _check_auth_by_bearer_header() -> UserId | None:
    """Authenticate the user via Bearer token in the HTTP_AUTHORIZATION header

    Returns:
        a UserId if authenticated successfully
        None if no matching header is found

    Raises:
        MKAuthException: when the header is found but the credentials are not valid
    """
    return _check_auth_by_header("Bearer", _parse_bearer_token)


def _check_internal_token() -> SiteInternalPseudoUser | None:
    if not (auth_header := request.environ.get("HTTP_AUTHORIZATION", "")).startswith(
        "InternalToken "
    ):
        return None

    _tokenname, token = auth_header.split("InternalToken ", maxsplit=1)

    with contextlib.suppress(binascii.Error):  # base64 decoding failure
        if SiteInternalSecret().check(Secret.from_b64(token)):
            return SiteInternalPseudoUser()

    return None


def _check_remote_site() -> RemoteSitePseudoUser | None:
    if not (auth_header := request.environ.get("HTTP_AUTHORIZATION", "")).startswith("RemoteSite "):
        return None

    _tokenname, token = auth_header.split("RemoteSite ", maxsplit=1)

    if (page_name := requested_file_name(request)) != "register_agent":
        raise MKAuthException(f"RemoteSite auth for invalid page: {page_name}")

    with contextlib.suppress(binascii.Error):  # base64 decoding failure
        for enabled_site in enabled_sites().values():
            if "secret" not in enabled_site:
                continue
            if Secret.from_b64(token).compare(Secret(enabled_site["secret"].encode())):
                return RemoteSitePseudoUser(enabled_site["id"])
    raise MKAuthException("RemoteSite auth for unknown remote site")


def _parse_bearer_token(token: str) -> tuple[str, str]:
    """Read username and password from a Bearer token ("<username> <password>").

    Examples:

        >>> _parse_bearer_token("username password")
        ('username', 'password')

        >>> _parse_bearer_token("username:password")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: ...

        >>> _parse_bearer_token(" ")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: ...

        Currently base64 encoded bearer tokens are not supported, although it would be useful:
        >>> _parse_bearer_token("SGFsbG8gV2VsdCE=")
        ... # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: ...
    """
    user_id, password = token.strip().split(" ", 1)
    return user_id, password


def _check_cme_login(user_id: UserId) -> None:
    """In case of CME, check that the customer is allowed to log in at this site"""
    if not userdb.is_customer_user_allowed_to_login(user_id):
        auth_logger.debug("User '%s' is not allowed to authenticate: Invalid customer", user_id)
        raise MKAuthException("Unknown customer. Can't log in.")


def _try_user_id(user_id: str) -> UserId:
    """Try wrapping a UserId, but throw an MKAuthException when impossible."""
    if not user_id:
        raise MKAuthException("Empty user not allowed.")
    try:
        return UserId(user_id)
    except ValueError as exc:
        raise MKAuthException("Illegal username.") from exc


def _verify_automation_login(user_id: UserId, secret: str) -> bool:
    """Verify an automation user secret.

    Returns:
        True if user_id is an automation user and the secret matches.
    """

    htpwd_entries = Htpasswd(cmk.utils.paths.htpasswd_file).load(allow_missing_file=True)
    password_hash = htpwd_entries.get(user_id)

    return (
        secret != ""
        and password_hash is not None
        and not password_hash.startswith("!")  # user is locked
        and password_hashing.matches(Password(secret), password_hash)
    )


def _verify_user_login(user_id: UserId, password: Password) -> bool:
    """Verify the user's login credentials.

    Returns:
        True if a userdb connector successfully verifies the user and password.
    """
    try:
        return bool(userdb.check_credentials(user_id, password, datetime.now()))
    except MKUserError:
        return False
