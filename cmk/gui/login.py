#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import contextlib
import http.client
from collections.abc import Iterator
from datetime import datetime
from typing import override
from urllib.parse import unquote

import cmk.ccc.version as cmk_version
from cmk.ccc.site import omd_site, url_prefix
from cmk.ccc.user import UserId

import cmk.utils.paths
from cmk.utils.licensing.handler import LicenseStateError, RemainingTrialTime
from cmk.utils.licensing.registry import get_remaining_trial_time_rounded
from cmk.utils.log.security_event import log_security_event
from cmk.utils.urls import is_allowed_url

import cmk.gui.mobile
from cmk.gui import userdb
from cmk.gui.auth import is_site_login
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import FinalizeRequest, HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import (
    LoggedInNobody,
    LoggedInRemoteSite,
    LoggedInSuperUser,
    LoggedInUser,
    user,
)
from cmk.gui.main import get_page_heading
from cmk.gui.pages import Page, PageEndpoint, PageRegistry
from cmk.gui.session import session, UserContext
from cmk.gui.theme.current_theme import theme
from cmk.gui.userdb import get_active_saml_connections
from cmk.gui.userdb.session import auth_cookie_name
from cmk.gui.utils import roles
from cmk.gui.utils.html import HTML
from cmk.gui.utils.login import show_saml2_login, show_user_errors
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.security_log_events import AuthenticationFailureEvent, AuthenticationSuccessEvent
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri, requested_file_name, urlencode
from cmk.gui.utils.user_errors import user_errors

from cmk.crypto.password import Password


def register(page_registry: PageRegistry) -> None:
    # TODO: only overwrite this in cse specific files
    if cmk_version.edition(cmk.utils.paths.omd_root) == cmk_version.Edition.CSE:
        page_registry.register(PageEndpoint("login", SaasLoginPage))
        page_registry.register(PageEndpoint("logout", SaasLogoutPage))
    else:
        page_registry.register(PageEndpoint("login", LoginPage))
        page_registry.register(PageEndpoint("logout", LogoutPage))


@contextlib.contextmanager
def authenticate() -> Iterator[bool]:
    """Perform the user authentication

    This is called by index.py to ensure user
    authentication and initialization of the user related data structures.

    Initialize the user session with the mod_python provided request object.
    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user and assume it as authenticated.

    Otherwise, we check / ask for the cookie authentication or eventually the
    automation secret authentication."""
    if isinstance(session.user, LoggedInNobody):
        yield False
    elif isinstance(session.user, LoggedInSuperUser | LoggedInRemoteSite):
        # This is used with the internaltoken auth
        # Let's hope we do not need the transactions for this user...
        yield True
    else:
        assert session.session_info.auth_type
        with TransactionIdContext(session.user.ident):
            yield True


@contextlib.contextmanager
def TransactionIdContext(user_id: UserId) -> Iterator[None]:
    """Managing context of authenticated user session with cleanup before logout.

    Args:
        user_id:
            The username.

    """
    with UserContext(user_id):
        try:
            yield
        finally:
            transactions.unignore()
            transactions.store_new()


def del_auth_cookie() -> None:
    cookie_name = auth_cookie_name()
    if not request.has_cookie(cookie_name):
        return

    response.unset_http_cookie(cookie_name)


class SaasLoginPage(Page):
    @override
    def page(self, config: Config) -> None:
        raise HTTPRedirect("cognito_sso.py")


class SaasLogoutPage(Page):
    @override
    def page(self, config: Config) -> None:
        raise HTTPRedirect("cognito_logout.py")


# TODO: Needs to be cleaned up. When using HTTP header auth or web server auth it is not
# ensured that a user exists after letting the user in. This is a problem for the following
# code! We need to define a point where the following code can rely on an existing user
# object. userdb.check_credentials() is doing some similar stuff
# - It also checks the type() of the user_id (Not in the same way :-/)
# - It also calls userdb.is_customer_user_allowed_to_login()
# - It calls userdb.create_non_existing_user() but we don't
# - It calls connection.is_locked() but we don't


class LoginPage(Page):
    def __init__(self) -> None:
        super().__init__()
        self._no_html_output = False
        self._username_varname = "_username"
        self._password_varname = "_password"

    def set_no_html_output(self, no_html_output: bool) -> None:
        self._no_html_output = no_html_output

    @override
    def page(self, config: Config) -> None:
        # Initialize the cmk.gui.i18n for the login dialog. This might be
        # overridden later after user login
        cmk.gui.i18n.localize(request.var("lang", config.default_language))

        self._do_login(config)

        if self._no_html_output:
            raise MKAuthException(_("Invalid login credentials."))

        if is_mobile(request, response):
            cmk.gui.mobile.page_login(config)
            return

        self._show_login_page(config)

    def _do_login(self, config: Config) -> None:
        """handle the login form"""
        if not request.var("_login"):
            return

        try:
            username: UserId | None = None  # make sure it's defined in the except block

            if not config.user_login and not is_site_login():
                raise MKUserError(None, _("Login is not allowed on this site."))

            # Login via the GET method is allowed only after manually
            # enabling the property "Enable login via GET" in the
            # Global Settings. Please refer to the Werk 14261 for
            # more details.
            if request.request_method != "POST" and not config.enable_login_via_get:
                raise MKUserError(None, _("Method not allowed"))

            username_var = request.get_str_input(self._username_varname, "")
            if not username_var:
                raise MKUserError(
                    self._username_varname, _("No username entered. Please enter a username.")
                )

            password_var = request.get_str_input(self._password_varname, "")
            if not password_var:
                raise MKUserError(
                    self._password_varname, _("No password entered. Please enter a password.")
                )

            try:
                username = UserId(username_var.rstrip())
                password = Password(password_var)
            except ValueError:
                # If type validation fails the credentials cannot be valid. Show the generic error.
                raise MKUserError(None, self._default_login_error_msg)

            default_origtarget = url_prefix() + "check_mk/"
            origtarget = request.get_url_input("_origtarget", default_origtarget)

            # Disallow redirections to:
            #  - logout.py: Happens after login
            #  - side.py: Happens when invalid login is detected during sidebar refresh
            if "logout.py" in origtarget or "side.py" in origtarget:
                origtarget = default_origtarget

            now = datetime.now()
            if result := userdb.check_credentials(username, password, now):
                # use the username provided by the successful login function, this function
                # might have transformed the username provided by the user. e.g. switched
                # from mixed case to lower case.
                username = result

                if roles.is_automation_user(username):
                    raise MKUserError(None, _("Automation user rejected"))

                # The login succeeded! Now:
                # a) Set the auth cookie
                # b) Unset the login vars in further processing
                # c) Redirect to really requested page
                session.login(LoggedInUser(username))

                # This must happen before the enforced password change is
                # checked in order to have the redirects correct...
                if userdb.is_two_factor_login_enabled(username):
                    raise HTTPRedirect(
                        "user_login_two_factor.py?_origtarget=%s" % urlencode(makeuri(request, []))
                    )

                # Having this before password updating to prevent redirect access issues
                if session.two_factor_enforced():
                    session.session_info.two_factor_required = True
                    raise HTTPRedirect(
                        "user_two_factor_enforce.py?_origtarget=%s"
                        % urlencode(makeuri(request, []))
                    )

                log_security_event(
                    AuthenticationSuccessEvent(
                        auth_method="login_form", username=username, remote_ip=request.remote_ip
                    )
                )

                # userdb.need_to_change_pw returns either None or the reason description why the
                # password needs to be changed
                if change_reason := userdb.need_to_change_pw(username, now):
                    raise HTTPRedirect(
                        f"user_change_pw.py?_origtarget={urlencode(origtarget)}&reason={change_reason}"
                    )

                # If user pasted e.g. a view to a link in mobile mode, redirect
                # to the correct page
                if is_mobile(request, response) and "start_url" in origtarget:
                    url = unquote(origtarget.split("start_url=")[1])
                    if not is_allowed_url(url):
                        url = default_origtarget
                    raise HTTPRedirect(url)

                raise HTTPRedirect(origtarget)

            userdb.on_failed_login(username, now)
            raise MKUserError(self._password_varname, self._default_login_error_msg)

        except MKUserError as e:
            log_security_event(
                AuthenticationFailureEvent(
                    user_error=e.message,
                    auth_method="login_form",
                    username=username,
                    remote_ip=request.remote_ip,
                )
            )
            user_errors.add(e)

    def _show_login_page(self, config: Config) -> None:
        html.render_headfoot = False
        html.add_body_css_class("login")
        make_header(html, get_page_heading(config), Breadcrumb())

        default_origtarget = (
            "index.py"
            if requested_file_name(request) in ["login", "logout"]
            else makeuri(request, [])
        )
        origtarget = request.get_url_input("_origtarget", default_origtarget)

        # Never allow the login page to be opened in the iframe. Redirect top page to login page.
        # This will result in a full screen login page.
        html.javascript(
            """if(top != self) {
    window.top.location.href = location;
}"""
        )

        # When someone calls the login page directly and is already authed redirect to main page
        if requested_file_name(request) == "login" and session.user.id:
            raise HTTPRedirect(origtarget)

        html.open_div(id_="login")

        html.open_div(id_="login_window")

        html.open_a(href="https://checkmk.com", class_="login_window_logo_link")
        html.img(
            src=theme.detect_icon_path(
                icon_name="login_logo" if theme.has_custom_logo("login_logo") else "checkmk_logo",
                prefix="",
            ),
            id_="logo",
        )
        html.close_a()

        try:
            _show_remaining_trial_time(get_remaining_trial_time_rounded())
        except LicenseStateError:
            pass

        with html.form_context("login", method="POST", add_transid=False, action="login.py"):
            html.hidden_field("_login", "1")
            html.hidden_field("_origtarget", origtarget)

            saml2_user_error: str | None = None
            if saml_connections := [
                c
                for c in get_active_saml_connections().values()
                if c["owned_by_site"] == omd_site()
            ]:
                saml2_user_error = show_saml2_login(saml_connections, saml2_user_error, origtarget)

            html.open_table()
            html.open_tr()
            html.td(
                html.render_label(
                    "%s:" % _("Username"),
                    id_="label_user",
                    class_=["legend"],
                    for_=self._username_varname,
                ),
                class_="login_label",
            )
            html.open_td(class_="login_input")
            html.text_input(self._username_varname, id_="input_user")
            html.close_td()
            html.close_tr()
            html.open_tr()
            html.td(
                html.render_label(
                    "%s:" % _("Password"),
                    id_="label_pass",
                    class_=["legend"],
                    for_=self._password_varname,
                ),
                class_="login_label",
            )
            html.open_td(class_="login_input")
            html.password_input(self._password_varname, id_="input_pass", size=None)
            html.close_td()
            html.close_tr()
            html.close_table()

            html.open_div(id_="button_text")
            html.button("_login", _("Login"), cssclass=None if saml_connections else "hot")
            html.close_div()

            if user_errors and not saml2_user_error:
                show_user_errors("login_error")

            html.close_div()

            html.open_div(id_="foot")

            if config.login_screen.get("login_message"):
                html.open_div(id_="login_message")
                html.show_message(config.login_screen["login_message"])
                html.close_div()

            footer: list[HTML] = []
            for title, url, target in config.login_screen.get("footer_links", []):
                footer.append(HTMLWriter.render_a(title, href=url, target=target))

            if "hide_version" not in config.login_screen:
                footer.append(HTML.with_escaping("Version: %s" % cmk_version.__version__))

            footer.append(
                HTML.without_escaping("&copy; ")
                + HTMLWriter.render_a("Checkmk GmbH", href="https://checkmk.com", target="_blank")
            )

            html.write_html(HTML.without_escaping(" - ").join(footer))

            html.close_div()

            html.set_focus(self._username_varname)
            html.hidden_fields()
        html.close_div()

        html.footer()

    @property
    def _default_login_error_msg(self) -> str:
        return _("Incorrect username or password. Please try again.")


def _show_remaining_trial_time(remaining_trial_time: RemainingTrialTime) -> None:
    # remaining_trial_time has already been adjusted for display purposes
    # so that 29d 23h turns into 30d
    # and 0d 0h 30m turns into 1h
    # Note: Once the actual remaining trial time <= 0 seconds,
    #       this code is not reached anymore (license switch from trial to free)
    remaining_days: int = remaining_trial_time.days
    remaining_hours: int = remaining_trial_time.hours
    remaining_percentage: float = remaining_trial_time.perc

    html.open_div(class_="trial_expiration_info" + (" warning" if remaining_days < 8 else ""))
    html.span(
        (
            _("%d days") % remaining_days
            if remaining_days > 1
            else "%d " % remaining_hours + ungettext("hour", "hours", remaining_hours)
        ),
        class_="remaining_time",
    )

    html.span(_(" left in your free trial"))

    html.open_div(class_="time_bar")
    html.div(
        "",
        class_="passed",
        style="width: %d%%;" % (100 - remaining_percentage),
    )
    html.div(
        "",
        class_="remaining",
        style="width: %d%%;" % remaining_percentage,
    )
    html.close_div()

    html.close_div()


class LogoutPage(Page):
    @override
    def page(self, config: Config) -> None:
        assert user.id is not None

        session.invalidate()
        session.persist()

        if session.session_info.auth_type == "cookie":
            raise HTTPRedirect(url_prefix() + "check_mk/login.py")

        # Implement HTTP logout with cookie hack
        if not request.has_cookie("logout"):
            response.headers["WWW-Authenticate"] = (
                'Basic realm="OMD Monitoring Site %s"' % omd_site()
            )
            response.set_http_cookie("logout", "1", secure=request.is_secure)
            raise FinalizeRequest(http.client.UNAUTHORIZED)

        response.delete_cookie("logout")
        raise HTTPRedirect(url_prefix() + "check_mk/")
