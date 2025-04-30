#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import contextlib
from collections.abc import Container, Iterator
from contextlib import AbstractContextManager as ContextManager
from datetime import datetime
from typing import cast, override

import flask
from flask import Flask
from flask.sessions import SessionInterface, SessionMixin

from cmk.ccc.exceptions import MKException
from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId

from cmk.utils.log.security_event import log_security_event

from cmk.gui import config, userdb
from cmk.gui.auth import (
    check_auth,
    parse_and_check_cookie,
)
from cmk.gui.exceptions import MKAuthException
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInNobody, LoggedInRemoteSite, LoggedInSuperUser, LoggedInUser
from cmk.gui.logged_in import user as logged_in_user
from cmk.gui.pseudo_users import PseudoUserId, RemoteSitePseudoUser, SiteInternalPseudoUser
from cmk.gui.type_defs import AuthType, SessionId, SessionInfo
from cmk.gui.userdb.session import auth_cookie_value
from cmk.gui.userdb.store import convert_idle_timeout, load_custom_attr
from cmk.gui.utils import roles
from cmk.gui.utils.flashed_messages import MsgType
from cmk.gui.utils.security_log_events import AuthenticationSuccessEvent
from cmk.gui.wsgi.utils import dict_property

from cmk import trace

tracer = trace.get_tracer()


class CheckmkFileBasedSession(dict, SessionMixin):
    new = True
    session_info = dict_property[SessionInfo]()
    exc = dict_property[MKException | None](default=None)
    is_gui_session = dict_property[bool](default=True)

    def update_cookie(self) -> None:
        # Cookies only get set when the session is new, so we make ourselves new again.
        self.new = True

    # The user instance is cached in the _user attribute for the duration of the request.
    @property
    def user(self) -> LoggedInUser:
        user = self.get("_user")
        if user is None:
            return LoggedInNobody()
        return user  # type: ignore[no-any-return]

    @user.setter
    def user(self, user: LoggedInUser) -> None:
        if not isinstance(user, LoggedInNobody | LoggedInSuperUser | LoggedInRemoteSite):
            assert user.id is not None
        self["_user"] = user

    @property
    def user_id(self):  # type: ignore[no-untyped-def]
        raise AttributeError("Don't set user_id please.")

    @property
    def persist_session(self) -> bool:
        if isinstance(self.user, LoggedInNobody | LoggedInSuperUser | LoggedInRemoteSite):
            return False

        if not self.is_gui_session:
            # No persistant sessions for RestAPI
            return False

        return not self.user.automation_user

    def initialize(
        self,
        user_name: UserId | None,
        auth_type: AuthType | None,
    ) -> None:
        now = datetime.now()
        if user_name is not None:
            userdb.session.ensure_user_can_init_session(user_name, datetime.now())
            self.user = LoggedInUser(user_name)
        else:
            self.user = LoggedInNobody()

        self.session_info = SessionInfo(
            session_id=userdb.session.create_session_id(),
            started_at=int(now.timestamp()),
            last_activity=int(now.timestamp()),
            flashes=[],
            auth_type=auth_type,
        )

    @classmethod
    def create_empty_session(cls, exc: MKException | None = None) -> CheckmkFileBasedSession:
        """Create a new and empty and logged-out session.

        This will lead to the session cookie being deleted.
        """
        sess = cls()
        sess.initialize(None, None)
        sess.exc = exc
        return sess

    @classmethod
    def create_session(
        cls,
        user_name: UserId,
        auth_type: AuthType,
    ) -> CheckmkFileBasedSession:
        sess = cls()
        sess.initialize(
            user_name,
            auth_type,
        )
        return sess

    @classmethod
    def create_pseudo_user_session(cls, pseudo_user_id: PseudoUserId) -> CheckmkFileBasedSession:
        """This method is reserved for pseudo users

        These should not really be sessions but currently everything is a session..."""

        sess = cls()
        match pseudo_user_id:
            case SiteInternalPseudoUser():
                sess.user = LoggedInSuperUser()
            case RemoteSitePseudoUser():
                sess.user = LoggedInRemoteSite(site_name=pseudo_user_id.site_name)
            case _:
                raise NotImplementedError
        return sess

    @classmethod
    def load_session(
        cls,
        user_name: UserId,
        session_id: SessionId,
    ) -> CheckmkFileBasedSession:
        """Load the session data from disk.

        Args:
            user_name:
            session_id:

        Returns:

        Raises:
            KeyError: when session_id is not in user's session.

        """
        now = datetime.now()
        session_infos = userdb.session.active_sessions(
            userdb.session.load_session_infos(user_name), now
        )
        if session_id not in session_infos:
            raise MKAuthException(f"Session {session_id} not found.")

        info = session_infos[session_id]
        if info.logged_out:
            raise MKAuthException("You have been logged out.")

        sess = cls()
        sess.user = LoggedInUser(user_name)
        sess.session_info = info
        # NOTE: This is only called from a "cookie" auth location. If you add more, refactor.
        sess.session_info.auth_type = "cookie"
        sess.new = False
        sess["_flashes"] = info.flashes
        return sess

    @tracer.instrument("CheckmkFileBas.login")
    def login(self, user_obj: LoggedInUser) -> None:
        userdb.session.on_succeeded_login(user_obj.ident, datetime.now())
        self.user = user_obj

    def persist(self) -> None:
        """Save the session as "session_info" custom user attribute"""
        self.session_info.flashes = self.get("_flashes", [])

        if not self.persist_session:
            return

        if self.user is None:
            raise RuntimeError("Can't persist a session without a user.")

        # Needs more context manager.
        session_infos = userdb.session.active_sessions(
            userdb.session.load_session_infos(self.user.ident, lock=True),
            datetime.now(),
        )

        # Check if the latest session persist was a logout, then keep the logged_out state
        if self.session_info.session_id in session_infos:
            if session_infos[self.session_info.session_id].logged_out is True:
                self.session_info.logged_out = True

        session_infos[self.session_info.session_id] = self.session_info
        userdb.session.save_session_infos(self.user.ident, session_infos)

    def invalidate(self) -> None:
        self.session_info.logged_out = True

    def is_expired(self, now: datetime) -> bool:
        """Check if session has expired either due to maximum duration or exceeded idle time."""
        session_duration = now.timestamp() - self.session_info.started_at
        max_duration = config.active_config.session_mgmt.get("max_duration", {}).get(
            "enforce_reauth"
        )
        if max_duration and session_duration > max_duration:
            return True

        assert self.user.id is not None

        idle_time = int(now.timestamp()) - self.session_info.last_activity
        idle_timeout = load_custom_attr(
            user_id=self.user.id, key="idle_timeout", parser=convert_idle_timeout
        )
        if idle_timeout is None:
            idle_timeout = config.active_config.session_mgmt.get("user_idle_timeout")

        return idle_timeout is not None and idle_timeout is not False and idle_time > idle_timeout

    def warn_if_session_expires_soon(self, now: datetime) -> None:
        """Warn user if they are close to maximum session duration only"""
        session_duration = now.timestamp() - self.session_info.started_at
        max_duration = config.active_config.session_mgmt.get("max_duration", {}).get(
            "enforce_reauth"
        )
        warning_threshold = config.active_config.session_mgmt.get("max_duration", {}).get(
            "enforce_reauth_warning_threshold"
        )
        if (
            max_duration
            and warning_threshold
            and (warning_threshold >= max_duration - session_duration)
        ):
            self._flash_message(
                "warning",
                _(
                    "Maximum session duration almost reached. Re-authenticate session to prevent data loss."
                ),
            )

    def _flash_message(self, msg_type: MsgType, message: str) -> None:
        """

        Copy of the flash.flash functionality.
        We cannot use original flask.flash method as we do not have a session within our request context

        """
        tuple_to_add = (msg_type, message)
        if tuple_to_add not in self.session_info.flashes:
            self.session_info.flashes.append(tuple_to_add)

    def two_factor_pending(self) -> bool:
        if isinstance(self.user, LoggedInNobody | LoggedInSuperUser):
            return False

        return (
            userdb.is_two_factor_login_enabled(self.user.ident)
            and not self.session_info.two_factor_completed
        )

    def two_factor_enforced(self) -> bool:
        return (
            config.active_config.require_two_factor_all_users
            or roles.is_two_factor_required(logged_in_user.ident)
        ) and not self.session_info.two_factor_completed


class FileBasedSession(SessionInterface):
    """A "session" which loads its information from a .mk file

    We need this because Checkmk's components expect this information to be available when:
     - a request context has been started,
     - even if no request has being started yet

    For Flask, the only way to fulfil these conditions is to create a session object.

    Ideally, this session should not be used for this purpose, as it prevents us from using it in
    the way it was intended to be used. The rest of the code should change to make it work.
    """

    session_class = CheckmkFileBasedSession

    @override
    def get_cookie_name(self, app: Flask) -> str:
        # NOTE: get_cookie_name and get_cookie_path are implemented at runtime (not with
        # app.settings[...]) to allow the Flask-App to be reused for different sites in
        # the tests.
        return f"auth_{omd_site()}"

    @override
    def get_cookie_path(self, app: Flask) -> str:
        # NOTE: get_cookie_name and get_cookie_path are implemented at runtime (not with
        # app.settings[...]) to allow the Flask-App to be reused for different sites in
        # the tests.
        return f"/{omd_site()}/"

    def _resume_session(self, app: Flask, request: flask.Request) -> CheckmkFileBasedSession | None:
        """Check if there is a session to resume to

        check if cookie is there and if it is valid. If so return the session
        otherwise return None"""

        if not (cookie_value := request.cookies.get(self.get_cookie_name(app), type=str)):
            # No cookie, nothing to resume
            return None

        try:
            user_name, session_id, _cookie_hash = parse_and_check_cookie(cookie_value)
            sess = self.session_class.load_session(user_name, session_id)
            sess.warn_if_session_expires_soon(datetime.now())
            if sess.is_expired(datetime.now()):
                return None
        except MKAuthException:
            # Catches an invalid cred issue checked by test_session.py
            return None
        return sess

    def _authenticate_and_open(self, app: Flask, request: flask.Request) -> CheckmkFileBasedSession:
        """Authenticate and open new session

        try to authenticate a request based on headers, password login is
        handled in login.py"""

        identity, auth_type = check_auth()

        if isinstance(identity, PseudoUserId):
            return self.session_class.create_pseudo_user_session(identity)

        user_name = identity

        userdb.session.on_succeeded_login(user_name, datetime.now())

        # Our REST API doesn't hand out session tokens, so every request is a new session.
        # Filter those for now to avoid spamming the log.
        if auth_type != "bearer":
            log_security_event(
                AuthenticationSuccessEvent(
                    auth_method=auth_type,
                    username=user_name,
                    remote_ip=request.remote_addr,
                )
            )

        self.update_last_login(user_name, auth_type, request)

        return self.session_class.create_session(user_name, auth_type)

    def update_last_login(
        self, userid: UserId, auth_type: AuthType, request: flask.Request
    ) -> None:
        last_login_info = {
            "auth_type": auth_type,
            "timestamp": int(datetime.now().timestamp()),
            "remote_address": request.remote_addr,
        }
        userdb.save_custom_attr(userid, "last_login", last_login_info)

    @override
    @tracer.instrument("FileBasedSession.open_session")
    def open_session(self, app: Flask, request: flask.Request) -> CheckmkFileBasedSession | None:
        # We need the config to be able to set the timeout values correctly.
        config.initialize()

        try:
            return self._resume_session(app, request) or self._authenticate_and_open(app, request)
        except MKAuthException as exc:
            return self.session_class.create_empty_session(exc=exc)

    # NOTE: The type-ignore[override] here is due to the fact, that any alternative would result
    # in multiple hundreds of lines changes and hundreds of mypy errors at this point and is thus
    # deferred to a later date.
    @override
    @tracer.instrument("FileBasedSession.save_session")
    def save_session(  # type: ignore[override]
        self, app: Flask, session: CheckmkFileBasedSession, response: flask.Response
    ) -> None:
        # NOTE
        # In order to log out, we need to do the following to prevent replay attacks:
        #
        # 1. Load the stored user-session and mark it as "invalidated".
        # 2. Remove the session cookie.
        #
        # Only removing the session cookie is not sufficient, as the user could just re-create it
        # and use the stale session again. We need to mark the session as "logged out".
        cookie_name = self.get_cookie_name(app)
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        secure = self.get_cookie_secure(app)
        expires = self.get_expiration_time(app, session)

        if not self.should_set_cookie(app, session):
            # This is the case when the session has not been modified.
            return

        if not session.persist_session:
            return

        if session.user.id is None:
            if not session.new:
                response.delete_cookie(cookie_name, path=path)
            return

        # NOTE
        # We need to save the session before deleting the cookie so that the logged-out status
        # will be persisted even if the user tries to reincarnate the session through a replay.
        session.session_info.last_activity = int(datetime.now().timestamp())
        session.persist()

        if session.session_info.logged_out:
            response.delete_cookie(cookie_name, path=path)
            return

        if session.new:
            cookie_value = auth_cookie_value(session.user.ident, session.session_info.session_id)
            response.set_cookie(
                cookie_name,
                cookie_value,
                expires=expires,
                httponly=True,
                domain=domain,
                path=path,
                secure=secure,
                samesite="Lax",
            )


# Casting the original LocalProxy, so "from flask import session" and our own
# session object will always return the same objects.
session: CheckmkFileBasedSession = cast(CheckmkFileBasedSession, flask.session)


@contextlib.contextmanager
def _UserContext(user_obj: LoggedInUser) -> Iterator[None]:
    """Managing authenticated user context

    After the user has been authenticated, initialize the global user object."""
    old_user: LoggedInUser = session.user
    session.user = user_obj
    try:
        yield
    finally:
        session.user = old_user


def UserContext(
    user_id: UserId,
    *,
    explicit_permissions: Container[str] = frozenset(),
) -> ContextManager[None]:
    """Execute a block of code as another user

    After the block exits, the previous user will be replaced again.
    """
    return _UserContext(
        LoggedInUser(
            user_id,
            explicitly_given_permissions=explicit_permissions,
        )
    )


def SuperUserContext() -> ContextManager[None]:
    """Execute a block code as the superuser

    After the block exits, the previous user will be replaced again.

    Returns:
        The context manager.

    """
    return _UserContext(LoggedInSuperUser())
