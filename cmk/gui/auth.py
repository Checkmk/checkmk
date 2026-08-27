#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"


import base64
import binascii
import contextlib
import hmac
import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import cmk.utils.paths
from cmk.ccc.user import UserId
from cmk.crypto import password_hashing
from cmk.crypto.password import Password
from cmk.crypto.secrets import Secret
from cmk.gui import userdb
from cmk.gui.authorization import Authorization
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.oauth.store.backend import StoreUnavailableError
from cmk.gui.oauth.store.token_store import get_token_store, looks_like_token, TokenRecord
from cmk.gui.pseudo_users import PseudoUserId, RemoteSitePseudoUser, SiteInternalPseudoUser
from cmk.gui.site_config import enabled_sites
from cmk.gui.type_defs import AuthType, CustomUserAttrSpec, UserSpec
from cmk.gui.user_connection_config_types import UserConnectionConfig
from cmk.gui.userdb import get_user_attributes, load_user, UserAttribute
from cmk.gui.userdb.session import generate_auth_hash
from cmk.gui.utils.htpasswd import Htpasswd
from cmk.gui.utils.security_log_events import AuthenticationFailureEvent
from cmk.utils.local_secrets import SiteInternalSecret
from cmk.utils.security_event import log_security_event
from cmk.web.utils.urls import requested_file_name

auth_logger = logger.getChild("auth")


AuthFunction = Callable[[Config], UserId | PseudoUserId | None]
CredentialFunction = Callable[[Config], "Credential | None"]


@dataclass(frozen=True, slots=True)
class Credential:
    """Who the request authenticated as, and what the credential it presented permits.

    A scoped OAuth token is the only credential that permits less than its user's roles do.
    """

    identity: UserId | PseudoUserId
    authorization: Authorization


def _unscoped(auth_function: AuthFunction) -> CredentialFunction:
    """Adapt an auth method that applies no scopes."""
    # This is wrapped around the _check functions rather than applied within them,
    # so those that return some PseudoUserId subclass can continue to do so explicitly.

    def _unscoped_auth(config: Config) -> Credential | None:
        identity = auth_function(config)
        return Credential(identity, Authorization.UNRESTRICTED) if identity is not None else None

    return _unscoped_auth


def check_auth(config: Config) -> tuple[Credential, AuthType]:
    """Try to authenticate a user from the current request.

    This will attempt to authenticate the user via all possible authentication types.
    If any of them succeeds, the credential it presented and the succeeding authentication type
    are returned.
    Some attempted authentication types may raise exceptions and abort this function preemptively.
    """
    if not config.user_login and not is_site_login():
        raise MKAuthException("Site can't be logged into.")

    auth_methods: list[tuple[CredentialFunction, AuthType]] = [
        # NOTE: This list is sorted from the more general to the most specific auth methods.
        #       The most specific to succeed will be used in the end.
        (_unscoped(_check_auth_by_custom_http_header), "http_header"),
        (_unscoped(_check_auth_by_remote_user), "web_server"),
        (_unscoped(_check_auth_by_basic_header), "basic_auth"),
        (_unscoped(_check_auth_by_bearer_header), "bearer"),
        (_unscoped(_check_internal_token), "internal_token"),
        (_check_auth_by_oauth_token, "oauth"),
        (_unscoped(_check_remote_site), "remote_site"),
    ]

    selected: tuple[Credential, AuthType] | None = None
    result = None
    for auth_method, auth_type in auth_methods:
        # NOTE: It's important for these methods to always raise an exception whenever something
        # strange is happening. This will abort the whole process, regardless of which auth method
        # succeeded or not.
        try:
            if result := auth_method(config):
                # The last auth_method is the most specific one, use that.
                selected = (result, auth_type)
        except Exception as e:
            log_security_event(
                AuthenticationFailureEvent(
                    user_error=str(e),
                    auth_method=auth_type,
                    username=(
                        result.identity if result and isinstance(result.identity, UserId) else None
                    ),
                    remote_ip=request.remote_ip,
                )
            )
            raise

    if not selected:
        raise MKAuthException("Couldn't log in.")

    credential, selected_auth_type = selected
    if not isinstance(credential.identity, PseudoUserId):
        _check_multi_tenancy_login(credential.identity)

    return credential, selected_auth_type


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


def _check_auth_by_custom_http_header(config: Config) -> UserId | None:
    """When http header auth is enabled, try to read the user_id from the var

    WARNING: This way of authentication does NOT verify any credentials!
    """
    if (auth_by_http_header := config.auth_by_http_header) and (
        username := request.headers.get(auth_by_http_header, type=str)
    ):
        return _try_user_id(username)

    return None


def _check_auth_by_remote_user(config: Config) -> UserId | None:
    """Try to get the authenticated user from the HTTP request

    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user.

    WARNING: This way of authentication does NOT verify any credentials!
    """
    if (username := request.remote_user) is None:
        return None  # type: ignore[unreachable]

    user_id = _try_user_id(username)
    if userdb.user_exists(user_id):
        return user_id

    raise MKAuthException(f"User {user_id} does not exist.")


def _check_auth_by_header(
    token_name: Literal["Basic", "Bearer"],
    parse_token: Callable[[str], tuple[str, str]],
    custom_user_attributes: Sequence[CustomUserAttrSpec],
    lock_on_logon_failures: int | None,
    log_logon_failures: bool,
    default_user_profile: UserSpec,
    user_connections: Sequence[UserConnectionConfig],
    pprint_value: bool,
    debug: bool,
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

    user_attributes = get_user_attributes(custom_user_attributes)

    # Could be an automation user or a regular user
    if _verify_automation_login(user_id, password.raw) or _verify_user_login(
        user_id,
        password,
        user_attributes,
        user_connections,
        default_user_profile,
        pprint_value=pprint_value,
        debug=debug,
    ):
        return user_id

    # At this point: invalid credentials. Could be user, password or both.
    # on_failed_login wants to be informed about non-existing users as well.
    userdb.on_failed_login(
        user_id,
        user_attributes,
        user_connections,
        now=datetime.now(),
        lock_on_logon_failures=lock_on_logon_failures,
        log_logon_failures=log_logon_failures,
        pprint_value=pprint_value,
    )

    raise MKAuthException(f"Wrong credentials ({token_name} header)")


def _check_auth_by_basic_header(config: Config) -> UserId | None:
    """Authenticate the user via Basic Auth token in the HTTP_AUTHORIZATION header

    Returns:
        a UserId if authenticated successfully
        None if no matching header is found

    Raises:
        MKAuthException: when the header is found but the credentials are not valid
        MKAuthException: when the user in REMOTE_USER is different to the one in HTTP_AUTHORIZATION
    """
    if not (
        user_id := _check_auth_by_header(
            "Basic",
            _parse_basic_auth_token,
            config.wato_user_attrs,
            config.lock_on_logon_failures,
            config.log_logon_failures,
            config.default_user_profile,
            config.user_connections,
            config.wato_pprint_config,
            config.debug,
        )
    ):
        return None

    # Even if the credentials verify that the user may log in, if these don't match, we
    # abort anyway, because this doesn't make any sense.
    if (remote_user := _check_auth_by_remote_user(config)) and user_id != remote_user:
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


def _check_oauth_access_token(token: str) -> TokenRecord | None:
    """Authenticate via an OAuth-issued access token.

    Returns:
        the token's record if the token exists, hasn't expired, and the user
        still exists and isn't locked
        None otherwise
    """
    # Authentication runs inside the Flask session interface, before the
    # request handling that would otherwise turn an unavailable store into a
    # 503 (see StoreUnavailableError) -- a token this site cannot check
    # authenticates nobody instead.
    try:
        with get_token_store() as store:
            record = store.get_by_token(token)
    except StoreUnavailableError:
        record = None
    if record is None or not record.is_valid():
        return None

    user_id = record.user_id
    if not userdb.user_exists(user_id) or userdb.user_locked(user_id, load_user(user_id)):
        return None

    return record


def _get_bearer_token() -> str | None:
    """Return the raw token from a Bearer Authorization header, or None if absent."""
    auth_header = request.environ.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return None
    return str(auth_header.removeprefix("Bearer ").strip())


def _is_oauth_shaped(token: str) -> bool:
    return " " not in token and looks_like_token(token)


def _check_auth_by_oauth_token(config: Config) -> Credential | None:
    """Authenticate via an OAuth-issued access token in the Bearer header.

    Returns:
        a Credential capped at what the token's scope permits, if authenticated
            successfully
        None if no Bearer header is present, or it isn't shaped like an
            OAuth access token

    Raises:
        MKAuthException: when the header is shaped like an OAuth token but
            isn't a valid one
    """
    if (token := _get_bearer_token()) is None or not _is_oauth_shaped(token):
        return None

    if (record := _check_oauth_access_token(token)) is not None:
        return Credential(record.user_id, Authorization.from_scopes(record.scope))

    raise MKAuthException("Invalid OAuth access token")


def _check_auth_by_bearer_header(config: Config) -> UserId | None:
    """Authenticate the user via a legacy "<username> <password>" Bearer token.

    Returns:
        a UserId if authenticated successfully
        None if no Bearer header is present, or it's shaped like an OAuth
            access token instead

    Raises:
        MKAuthException: when the header is found but the credentials are
            not valid
    """
    if (token := _get_bearer_token()) is None or _is_oauth_shaped(token):
        return None

    return _check_auth_by_header(
        "Bearer",
        _parse_bearer_token,
        config.wato_user_attrs,
        config.lock_on_logon_failures,
        config.log_logon_failures,
        config.default_user_profile,
        config.user_connections,
        config.wato_pprint_config,
        config.debug,
    )


def _check_internal_token(config: Config) -> SiteInternalPseudoUser | None:
    if not (auth_header := request.environ.get("HTTP_AUTHORIZATION", "")).startswith(
        "InternalToken "
    ):
        return None

    _tokenname, token = auth_header.split("InternalToken ", maxsplit=1)

    with contextlib.suppress(binascii.Error):  # base64 decoding failure
        if SiteInternalSecret().check(Secret.from_b64(token)):
            return SiteInternalPseudoUser()

    return None


# Pages that accept the distributed-setup site secret (``RemoteSite``
# Authorization scheme). Each entry is the page name of a (registered) page
# handler that authenticates the caller as a ``RemoteSitePseudoUser`` and
# either skips user-permission checks or scopes them to the site secret.
# Keep in sync with the ``PageEndpoint`` registrations using these names.
_REMOTE_SITE_ALLOWED_PAGES: frozenset[str] = frozenset(
    {
        "register_agent",
        "proxy_download_agent",
    }
)


def _check_remote_site(config: Config) -> RemoteSitePseudoUser | None:
    if not (auth_header := request.environ.get("HTTP_AUTHORIZATION", "")).startswith("RemoteSite "):
        return None

    _tokenname, token = auth_header.split("RemoteSite ", maxsplit=1)

    if (page_name := requested_file_name(request)) not in _REMOTE_SITE_ALLOWED_PAGES:
        raise MKAuthException(f"RemoteSite auth for invalid page: {page_name}")

    with contextlib.suppress(binascii.Error):  # base64 decoding failure
        for enabled_site in enabled_sites(config.sites).values():
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


def _check_multi_tenancy_login(user_id: UserId) -> None:
    """In multi-tenancy sites, check that the customer is allowed to log in to this site"""
    if not userdb.is_customer_user_allowed_to_login(user_id, load_user(user_id)):
        auth_logger.debug(
            "User '%(user_id)s' is not allowed to authenticate: Invalid customer",
            {"user_id": user_id},
        )
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


def _verify_user_login(
    user_id: UserId,
    password: Password,
    user_attributes: Sequence[tuple[str, UserAttribute]],
    user_connections: Sequence[UserConnectionConfig],
    default_user_profile: UserSpec,
    *,
    pprint_value: bool,
    debug: bool,
) -> bool:
    """Verify the user's login credentials.

    Returns:
        True if a userdb connector successfully verifies the user and password.
    """
    try:
        return bool(
            userdb.check_credentials(
                user_id,
                password,
                user_attributes,
                user_connections,
                datetime.now(),
                default_user_profile,
                pprint_value=pprint_value,
                debug=debug,
            )
        )
    except MKUserError:
        return False
