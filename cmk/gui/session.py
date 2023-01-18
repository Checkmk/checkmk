#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import cast, Container, ContextManager, Iterator

import flask
from flask import Flask
from flask.sessions import SessionInterface, SessionMixin

from cmk.utils.site import omd_site
from cmk.utils.type_defs import UserId

import cmk.gui.userdb.session  # NOQA  # pylint: disable=unused-import
from cmk.gui import config, userdb
from cmk.gui.auth import (
    _check_auth,
    _fetch_cookie,
    auth_logger,
    check_parsed_auth_cookie,
    user_from_cookie,
)
from cmk.gui.exceptions import MKAuthException
from cmk.gui.logged_in import LoggedInNobody, LoggedInSuperUser, LoggedInUser
from cmk.gui.type_defs import AuthType, SessionId, SessionInfo
from cmk.gui.userdb.session import auth_cookie_name, auth_cookie_value
from cmk.gui.wsgi.utils import dict_property


class CheckmkFileBasedSession(dict, SessionMixin):
    new = True

    session_info = dict_property[SessionInfo]()
    persist_session = dict_property[bool]()

    def update_cookie(self):
        # Cookies only get set when the session is new, so we make ourselves new again.
        self.new = True

    # The user instance is cached in the _user attribute for the duration of the request.
    @property
    def user(self) -> LoggedInUser:
        user = self.get("_user")
        if user is None:
            return LoggedInNobody()
        return user

    @user.setter
    def user(self, user: LoggedInUser) -> None:
        if not isinstance(user, (LoggedInNobody, LoggedInSuperUser)):
            assert user.id is not None
        self["_user"] = user

    @property
    def user_id(self):
        raise AttributeError("Don't set user_id please.")

    def initialize(
        self,
        user_name: UserId | None,
        auth_type: AuthType | None,
        persist: bool = True,
    ) -> None:
        now = datetime.now()
        if user_name is not None:
            userdb.session.ensure_user_can_init_session(user_name, datetime.now())
            self.user = LoggedInUser(user_name)
        else:
            self.user = LoggedInNobody()
        self.persist_session = persist
        self.session_info = SessionInfo(
            session_id=userdb.session.create_session_id(),
            started_at=int(now.timestamp()),
            last_activity=int(now.timestamp()),
            flashes=[],
            auth_type=auth_type,
        )

    @classmethod
    def create_empty_session(cls):
        sess = cls()
        sess.initialize(None, None)
        return sess

    @classmethod
    def create_session(
        cls,
        user_name: UserId,
        auth_type: AuthType,
        persist: bool = True,
    ) -> CheckmkFileBasedSession:
        sess = cls()
        sess.initialize(
            user_name,
            auth_type,
            persist=persist,
        )
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
        info = session_infos[session_id]
        if info.logged_out:
            return cls.create_empty_session()

        sess = cls()
        sess.user = LoggedInUser(user_name)
        sess.persist_session = True
        sess.session_info = info
        # NOTE: This is only called from a "cookie" auth location. If you add more, refactor.
        sess.session_info.auth_type = "cookie"
        sess.new = False
        sess["_flashes"] = info.flashes
        return sess

    @classmethod
    def from_cookie(cls, cookie_string: str) -> CheckmkFileBasedSession:
        user_name, session_id, _cookie_hash = user_from_cookie(cookie_string)
        try:
            userdb.on_access(user_name, session_id, datetime.now())
            return cls.load_session(user_name, session_id)
        except (KeyError, MKAuthException):
            return cls.create_empty_session()

    def persist(self):
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
        if self.session_info.logged_out and self.session_info.session_id in session_infos:
            # Logged out but still saved. We remove the entry and save it.
            del session_infos[self.session_info.session_id]
        else:
            session_infos[self.session_info.session_id] = self.session_info

        userdb.session.save_session_infos(self.user.ident, session_infos)

    def invalidate(self):
        self.session_info.logged_out = True


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

    def get_cookie_name(self, app: "Flask") -> str:
        # NOTE: get_cookie_name and get_cookie_path are implemented at runtime (not with
        # app.settings[...]) to allow the Flask-App to be reused for different sites in
        # the tests.
        return f"auth_{omd_site()}"

    def get_cookie_path(self, app: "Flask") -> str:
        # NOTE: get_cookie_name and get_cookie_path are implemented at runtime (not with
        # app.settings[...]) to allow the Flask-App to be reused for different sites in
        # the tests.
        return f"/{omd_site()}/"

    def open_session(self, app: Flask, request: flask.Request) -> CheckmkFileBasedSession | None:
        # In order to log in a user, we need to do the following:
        #
        # 1. In the login page, validate the user, persist the current session.
        # 2. In the session opener, we only validate that there actually is a session. If there is
        #    not, or it is marked as "logged out", we deny the user access.
        #
        # We need the config to be able to set the timeout values correctly.
        config.initialize()

        try:
            user_name, auth_type = _check_auth()
        except MKAuthException:
            return self.session_class.create_empty_session()

        now = datetime.now()

        if auth_type in ("cookie", "web_server", "http_header"):
            val = request.cookies.get(self.get_cookie_name(app), type=str)
            if not val:
                userdb.session.on_succeeded_login(user_name, now)
                return self.session_class.create_session(user_name, auth_type)

            _session = self.session_class.from_cookie(val)
            return _session

        return self.session_class.create_session(user_name, auth_type, persist=False)

    # NOTE: The type-ignore[override] here is due to the fact, that any alternative would result
    # in multiple hundreds of lines changes and hundreds of mypy errors at this point and is thus
    # deferred to a later date.
    def save_session(  # type: ignore[override]  # pylint: disable=redefined-outer-name
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
        samesite = self.get_cookie_samesite(app)
        httponly = self.get_cookie_httponly(app)
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
                httponly=httponly,
                domain=domain,
                path=path,
                secure=secure,
                samesite=samesite,
            )


def is_two_factor_completed() -> bool:
    """Whether or not the user has completed the 2FA challenge"""
    return session.session_info.two_factor_completed


def set_two_factor_completed() -> None:
    session.session_info.two_factor_completed = True


# Casting the original LocalProxy, so "from flask import session" and our own
# session object will always return the same objects.
session: CheckmkFileBasedSession = cast(CheckmkFileBasedSession, flask.session)


def get_session_id_from_cookie(username: UserId, revalidate_cookie: bool) -> str:
    cookie_username, session_id, cookie_hash = user_from_cookie(_fetch_cookie(auth_cookie_name()))

    # Has been checked before, but validate before using that information, just to be sure
    if revalidate_cookie:
        check_parsed_auth_cookie(username, session_id, cookie_hash)

    if cookie_username != username:
        auth_logger.error("Invalid session: (User: %s, Session: %s)", username, session_id)
        return ""

    return session_id


def auth_cookie_is_valid(cookie_text: str) -> bool:
    try:
        check_parsed_auth_cookie(*user_from_cookie(cookie_text))
        return True
    except MKAuthException:
        return False
    except Exception:
        return False


@contextlib.contextmanager
def _UserContext(user_obj: LoggedInUser) -> Iterator[None]:
    """Managing authenticated user context

    After the user has been authenticated, initialize the global user object."""
    old_user: LoggedInUser = session.user
    try:
        session.user = user_obj
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
