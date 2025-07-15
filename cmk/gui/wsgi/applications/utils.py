#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import abc
import functools
from collections.abc import Callable
from datetime import datetime
from typing import final
from wsgiref.types import StartResponse, WSGIEnvironment

import cmk.ccc.store
import cmk.ccc.version as cmk_version
from cmk.ccc.site import url_prefix

import cmk.utils.paths

import cmk.gui.auth
import cmk.gui.session
from cmk.gui import login, pages, userdb
from cmk.gui.config import Config
from cmk.gui.crash_handler import handle_exception_as_gui_crash_report
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUnauthenticatedException
from cmk.gui.http import request, Response, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInRemoteSite, LoggedInSuperUser, user
from cmk.gui.session import session
from cmk.gui.theme.current_theme import theme
from cmk.gui.utils.language_cookie import set_language_cookie
from cmk.gui.utils.urls import makeuri, makeuri_contextless, requested_file_name, urlencode
from cmk.gui.utils.user_frontend_settings_cookie import set_user_frontend_config_cookie
from cmk.gui.wsgi.type_defs import WSGIResponse

from cmk import trace

# TODO
#  * derive all exceptions from werkzeug's http exceptions.


class AbstractWSGIApp(abc.ABC):
    __slots__ = ("debug",)

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug

    @final
    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        return self.wsgi_app(environ, start_response)

    @abc.abstractmethod
    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        raise NotImplementedError


def ensure_authentication(
    handler: type[pages.Page] | pages.PageHandlerFunc,
) -> Callable[[Config], Response]:
    # Ensure the user is authenticated. This call is wrapping all the different
    # authentication modes the Checkmk GUI supports and initializes the logged-in
    # user objects.
    @functools.wraps(handler)
    def _call_auth(config: Config) -> Response:
        with login.authenticate() as authenticated:
            if not authenticated:
                return _handle_not_authenticated(config)

            if isinstance(session.user, LoggedInRemoteSite | LoggedInSuperUser):
                if isinstance(handler, type):
                    handler().handle_page(config)
                else:
                    handler(config)
                return response

            user_id = session.user.ident

            trace.get_current_span().set_attribute("cmk.auth.user_id", str(user_id))

            two_factor_login_pages = requested_file_name(request) in (
                "user_login_two_factor",
                "user_webauthn_login_begin",
                "user_webauthn_login_complete",
            )

            two_factor_registration_pages = requested_file_name(request) in (
                "user_two_factor_enforce",
                "user_totp_register",
                "user_webauthn_register_begin",
                "user_webauthn_register_complete",
            )

            # Two factor login
            if not two_factor_login_pages and session.two_factor_pending():
                raise HTTPRedirect(
                    "user_login_two_factor.py?_origtarget=%s" % urlencode(makeuri(request, []))
                )

            # Enforce Two Factor
            if (
                not two_factor_registration_pages
                and session.session_info.two_factor_required
                and not session.session_info.two_factor_completed
            ):
                raise HTTPRedirect(
                    "user_two_factor_enforce.py?_origtarget=%s" % urlencode(makeuri(request, []))
                )

            if (
                not two_factor_registration_pages
                and not two_factor_login_pages
                and requested_file_name(request) != "user_change_pw"
            ):
                if change_reason := userdb.need_to_change_pw(user_id, datetime.now()):
                    raise HTTPRedirect(
                        f"user_change_pw.py?_origtarget={urlencode(makeuri(request, []))}&reason={change_reason}"
                    )

            # When displaying the crash report message, the user authentication context
            # has already been left. We need to preserve this information to be able to
            # show the correct message for the current user.
            g.may_see_crash_reports = user.may("general.see_crash_reports")

            # This may raise an exception with error messages, which will then be displayed to
            # the user.
            _ensure_general_access()

            # Initialize the multisite cmk.gui.i18n. This will be replaced by
            # language settings stored in the user profile after the user
            # has been initialized
            _localize_request()

            # Update the UI theme with the attribute configured by the user.
            # Returns None on first load
            assert user.id is not None
            theme.set(
                cmk.gui.userdb.load_custom_attr(user_id=user.id, key="ui_theme", parser=lambda x: x)
            )

            set_user_frontend_config_cookie(request, response, user.frontend_config)

            if isinstance(handler, type):
                handler().handle_page(config)
            else:
                handler(config)

            return response

    return _call_auth


def plain_error() -> bool:
    """Webservice functions may decide to get a normal result code
    but a text with an error message in case of an error"""
    return request.has_var("_plain_error")


def fail_silently() -> bool:
    """Ajax-Functions want no HTML output in case of an error but
    just a plain server result code of 500"""
    return request.has_var("_ajaxid")


def _ensure_general_access() -> None:
    if user.may("general.use"):
        return

    reason = [
        _("You are not authorized to use the Checkmk GUI. Sorry. You are logged in as <b>%s</b>.")
        % user.id
    ]

    if user.role_ids:
        reason.append(_("Your roles are <b>%s</b>.") % ", ".join(user.role_ids))
    else:
        reason.append(_("<b>You do not have any roles.</b>"))

    reason.append(
        _(
            "If you think this is an error, please ask your administrator "
            "to check the permissions configuration."
        )
    )

    if session.session_info.auth_type == "cookie":
        reason.append(
            _("<p>You have been logged out. Please reload the page to re-authenticate.</p>")
        )
        login.del_auth_cookie()

    raise MKAuthException(" ".join(reason))


def _handle_not_authenticated(config: Config) -> Response:
    if fail_silently():
        # While api call don't show the login dialog
        raise MKUnauthenticatedException(_("You are not authenticated."))

    # Redirect to the login-dialog with the current url as original target
    # Never render the login form directly when accessing urls like "index.py"
    # or "dashboard.py". This results in strange problems.
    requested_file = requested_file_name(request)
    if requested_file != "login":
        post_login_url = makeuri(request, [])
        if requested_file != "index":
            # Ensure that users start with a navigation after they have logged in
            post_login_url = makeuri_contextless(
                request, [("start_url", post_login_url)], filename="index.py"
            )
        raise HTTPRedirect(
            f"{url_prefix()}check_mk/login.py?_origtarget={urlencode(post_login_url)}"
        )

    # This either displays the login page or validates the information submitted
    # to the login form. After successful login a http redirect to the originally
    # requested page is performed.
    if cmk_version.edition(cmk.utils.paths.omd_root) == cmk_version.Edition.CSE:
        from cmk.gui.cse.userdb.cognito.pages import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
            SingleSignOn,
        )

        saas_login_page = SingleSignOn()
        saas_login_page.handle_page(config)
    else:
        login_page = login.LoginPage()
        login_page.set_no_html_output(plain_error())
        login_page.handle_page(config)

    return response


def _localize_request() -> None:
    if user_language := request.get_ascii_input("lang", user.language):
        set_language_cookie(request, response, user_language)
        cmk.gui.i18n.localize(user_language)


def handle_unhandled_exception() -> Response:
    handle_exception_as_gui_crash_report(
        plain_error=plain_error(),
        fail_silently=fail_silently(),
        show_crash_link=getattr(g, "may_see_crash_reports", False),
    )
    # This needs to be cleaned up.
    return response
