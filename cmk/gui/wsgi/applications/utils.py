#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
from typing import Any, Callable, Dict

import cmk.utils.paths
import cmk.utils.profile
import cmk.utils.store
from cmk.utils.site import url_prefix

from cmk.gui import login, pages
from cmk.gui.crash_handler import handle_exception_as_gui_crash_report
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUnauthenticatedException
from cmk.gui.globals import g, request, response
from cmk.gui.http import Response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.utils.language_cookie import set_language_cookie
from cmk.gui.utils.theme import theme
from cmk.gui.utils.urls import makeuri, makeuri_contextless, requested_file_name, urlencode

# TODO
#  * derive all exceptions from werkzeug's http exceptions.


def ensure_authentication(func: pages.PageHandlerFunc) -> Callable[[], Response]:
    # Ensure the user is authenticated. This call is wrapping all the different
    # authentication modes the Checkmk GUI supports and initializes the logged
    # in user objects.
    @functools.wraps(func)
    def _call_auth() -> Response:
        with login.authenticate(request) as authenticated:
            if not authenticated:
                return _handle_not_authenticated()

            # When displaying the crash report message, the user authentication context
            # has already been left. We need to preserve this information to be able to
            # show the correct message for the current user.
            g.may_see_crash_reports = user.may("general.see_crash_reports")

            # This may raise an exception with error messages, which will then be displayed to the user.
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

            func()

            return response

    return _call_auth


def plain_error() -> bool:
    """Webservice functions may decide to get a normal result code
    but a text with an error message in case of an error"""
    return request.has_var("_plain_error") or requested_file_name(request) == "webapi"


def fail_silently() -> bool:
    """Ajax-Functions want no HTML output in case of an error but
    just a plain server result code of 500"""
    return request.has_var("_ajaxid")


def _ensure_general_access() -> None:
    if user.may("general.use"):
        return

    reason = [
        _(
            "You are not authorized to use the Check_MK GUI. Sorry. "
            "You are logged in as <b>%s</b>."
        )
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

    if login.auth_type == "cookie":  # type: ignore[has-type]
        reason.append(
            _("<p>You have been logged out. Please reload the page " "to re-authenticate.</p>")
        )
        login.del_auth_cookie()

    raise MKAuthException(" ".join(reason))


def _handle_not_authenticated() -> Response:
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
            "%scheck_mk/login.py?_origtarget=%s" % (url_prefix(), urlencode(post_login_url))
        )

    # This either displays the login page or validates the information submitted
    # to the login form. After successful login a http redirect to the originally
    # requested page is performed.
    login_page = login.LoginPage()
    login_page.set_no_html_output(plain_error())
    login_page.handle_page()

    return response


def _localize_request() -> None:
    user_language = request.get_ascii_input("lang", user.language)
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


def load_gui_log_levels() -> Dict[str, int]:
    """Load the GUI log level global setting from the WATO GUI config"""
    return load_single_global_wato_setting("log_levels", {"cmk.web": 30})


def load_single_global_wato_setting(varname: str, deflt: Any = None) -> Any:
    """Load a single config option from WATO globals (Only for special use)

    This is a small hack to get access to the current configuration without
    the need to load the whole GUI config.

    The problem is: The profiling setting is needed before the GUI config
    is loaded regularly. This is needed, because we want to be able to
    profile our whole WSGI app, including the config loading logic.

    We only process the WATO written global settings file to get the WATO
    settings. Which should be enough for the most cases.
    """
    settings = cmk.utils.store.load_mk_file(
        cmk.utils.paths.default_config_dir + "/multisite.d/wato/global.mk", default={}
    )
    return settings.get(varname, deflt)
