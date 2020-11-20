#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable
import functools

import cmk.utils.paths
import cmk.utils.profile
import cmk.utils.store

from cmk.gui import config, login, pages, modules
from cmk.gui.crash_reporting import handle_exception_as_gui_crash_report
from cmk.gui.exceptions import (
    MKAuthException,
    MKUnauthenticatedException,
    HTTPRedirect,
)
from cmk.gui.globals import html, request, g
from cmk.gui.i18n import _
from cmk.gui.utils.urls import makeuri
from cmk.gui.http import Response

# TODO
#  * derive all exceptions from werkzeug's http exceptions.


def ensure_authentication(func: pages.PageHandlerFunc) -> Callable[[], Response]:
    # Ensure the user is authenticated. This call is wrapping all the different
    # authentication modes the Checkmk GUI supports and initializes the logged
    # in user objects.
    @functools.wraps(func)
    def _call_auth():
        with login.authenticate(request) as authenticated:
            if not authenticated:
                return _handle_not_authenticated()

            # When displaying the crash report message, the user authentication context
            # has already been left. We need to preserve this information to be able to
            # show the correct message for the current user.
            g.may_see_crash_reports = config.user.may("general.see_crash_reports")

            # This may raise an exception with error messages, which will then be displayed to the user.
            _ensure_general_access()

            # Initialize the multisite cmk.gui.i18n. This will be replaced by
            # language settings stored in the user profile after the user
            # has been initialized
            _localize_request()

            # Update the UI theme with the attribute configured by the user.
            # Returns None on first load
            assert config.user.id is not None
            theme = cmk.gui.userdb.load_custom_attr(config.user.id, 'ui_theme', lambda x: x)
            html.set_theme(theme)

            func()

            return html.response

    return _call_auth


def plain_error() -> bool:
    """Webservice functions may decide to get a normal result code
    but a text with an error message in case of an error"""
    return html.request.has_var("_plain_error") or html.myfile == "webapi"


def fail_silently() -> bool:
    """Ajax-Functions want no HTML output in case of an error but
    just a plain server result code of 500"""
    return html.request.has_var("_ajaxid")


def _ensure_general_access() -> None:
    if config.user.may("general.use"):
        return

    reason = [
        _("You are not authorized to use the Check_MK GUI. Sorry. "
          "You are logged in as <b>%s</b>.") % config.user.id
    ]

    if config.user.role_ids:
        reason.append(_("Your roles are <b>%s</b>.") % ", ".join(config.user.role_ids))
    else:
        reason.append(_("<b>You do not have any roles.</b>"))

    reason.append(
        _("If you think this is an error, please ask your administrator "
          "to check the permissions configuration."))

    if login.auth_type == 'cookie':
        reason.append(
            _("<p>You have been logged out. Please reload the page "
              "to re-authenticate.</p>"))
        login.del_auth_cookie()

    raise MKAuthException(" ".join(reason))


def _handle_not_authenticated() -> Response:
    if fail_silently():
        # While api call don't show the login dialog
        raise MKUnauthenticatedException(_('You are not authenticated.'))

    # Redirect to the login-dialog with the current url as original target
    # Never render the login form directly when accessing urls like "index.py"
    # or "dashboard.py". This results in strange problems.
    if html.myfile != 'login':
        raise HTTPRedirect('%scheck_mk/login.py?_origtarget=%s' %
                           (config.url_prefix(), html.urlencode(makeuri(request, []))))
    # This either displays the login page or validates the information submitted
    # to the login form. After successful login a http redirect to the originally
    # requested page is performed.
    login_page = login.LoginPage()
    login_page.set_no_html_output(plain_error())
    login_page.handle_page()

    return html.response


def load_all_plugins() -> None:
    # Optimization: in case of the graph ajax call only check the metrics module. This
    # improves the performance for these requests.
    # TODO: CLEANUP: Move this to the pagehandlers if this concept works out.
    # werkzeug.wrappers.Request.script_root would be helpful here, but we don't have that yet.
    only_modules = ["metrics"] if html.myfile == "ajax_graph" else None
    modules.load_all_plugins(only_modules=only_modules)


def _localize_request() -> None:
    previous_language = cmk.gui.i18n.get_current_language()
    user_language = html.request.get_ascii_input("lang", config.user.language)

    html.set_language_cookie(user_language)
    cmk.gui.i18n.localize(user_language)

    # All plugins might have to be reloaded due to a language change. Only trigger
    # a second plugin loading when the user is really using a custom localized GUI.
    # Otherwise the load_all_plugins() at the beginning of the request is sufficient.
    if cmk.gui.i18n.get_current_language() != previous_language:
        load_all_plugins()


def handle_unhandled_exception() -> Response:
    handle_exception_as_gui_crash_report(
        plain_error=plain_error(),
        fail_silently=fail_silently(),
        show_crash_link=getattr(g, "may_see_crash_reports", False),
    )
    # This needs to be cleaned up.
    return html.response
