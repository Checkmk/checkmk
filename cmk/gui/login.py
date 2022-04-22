#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import http.client
import os
import traceback
from contextlib import suppress
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Union

from six import ensure_str
from werkzeug.local import LocalProxy

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.site import omd_site, url_prefix
from cmk.utils.type_defs import UserId

import cmk.gui.i18n
import cmk.gui.mobile
import cmk.gui.userdb as userdb
import cmk.gui.utils as utils
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import request_local_attr
from cmk.gui.exceptions import (
    FinalizeRequest,
    HTTPRedirect,
    MKAuthException,
    MKInternalError,
    MKUserError,
)
from cmk.gui.globals import html, request, response, theme, user_errors
from cmk.gui.htmllib import HTML
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user, UserContext
from cmk.gui.main import get_page_heading
from cmk.gui.pages import Page, page_registry
from cmk.gui.type_defs import AuthType
from cmk.gui.utils.escaping import escape_to_html
from cmk.gui.utils.language_cookie import del_language_cookie
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri, requested_file_name, urlencode

auth_logger = logger.getChild("auth")


@contextlib.contextmanager
def authenticate(req: Request) -> Iterator[bool]:
    """Perform the user authentication

    This is called by index.py to ensure user
    authentication and initialization of the user related data structures.

    Initialize the user session with the mod_python provided request object.
    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user and assume it as authenticated.

    Otherwise we check / ask for the cookie authentication or eventually the
    automation secret authentication."""

    user_id = _check_auth(req)
    if not user_id:
        yield False
        return

    with UserSessionContext(user_id):
        yield True


@contextlib.contextmanager
def UserSessionContext(user_id: UserId) -> Iterator[None]:
    """Managing context of authenticated user session with cleanup before logout."""
    with UserContext(user_id):
        try:
            yield
        finally:
            transactions.store_new()
            userdb.on_end_of_request(user_id, datetime.now())


def auth_cookie_name() -> str:
    return "auth%s" % site_cookie_suffix()


def site_cookie_suffix() -> str:
    prefix = url_prefix()

    # Strip of eventual present "http://<host>". DIRTY!
    if prefix.startswith("http:"):
        prefix = prefix[prefix[7:].find("/") + 7 :]

    return os.path.dirname(prefix).replace("/", "_")


def _load_secret() -> str:
    """Reads the sites auth secret from a file

    Creates the files if it does not exist. Having access to the secret means that one can issue
    valid cookies for the cookie auth.
    """
    htpasswd_path = Path(cmk.utils.paths.htpasswd_file)
    secret_path = htpasswd_path.parent.joinpath("auth.secret")

    secret = ""
    if secret_path.exists():
        with secret_path.open(encoding="utf-8") as f:
            secret = f.read().strip()

    # Create new secret when this installation has no secret
    #
    # In past versions we used another bad approach to generate a secret. This
    # checks for such secrets and creates a new one. This will invalidate all
    # current auth cookies which means that all logged in users will need to
    # renew their login after update.
    if secret == "" or len(secret) == 32:
        secret = _generate_secret()
        with secret_path.open("w", encoding="utf-8") as f:
            f.write(secret)

    return secret


def _generate_secret() -> str:
    return utils.get_random_string(256)


def _load_serial(username: UserId) -> int:
    """Load the password serial of the user

    This serial identifies the current config state of the user account. If either the password is
    changed or the account gets locked the serial is increased and all cookies get invalidated.
    Better use the value from the "serials.mk" file, instead of loading the whole user database via
    load_users() for performance reasons.
    """
    serial = userdb.load_custom_attr(user_id=username, key="serial", parser=int)
    return 0 if serial is None else serial


def _generate_auth_hash(username: UserId, session_id: str) -> str:
    return _generate_hash(username, username + session_id)


def _generate_hash(username: UserId, value: str) -> str:
    """Generates a hash to be added into the cookie value"""
    secret = _load_secret()
    serial = _load_serial(username)
    return sha256((value + str(serial) + secret).encode()).hexdigest()


def del_auth_cookie() -> None:
    cookie_name = auth_cookie_name()
    if not request.has_cookie(cookie_name):
        return

    cookie = _fetch_cookie(cookie_name)
    if auth_cookie_is_valid(cookie):
        response.delete_cookie(cookie_name)


def _auth_cookie_value(username: UserId, session_id: str) -> str:
    return ":".join([username, session_id, _generate_auth_hash(username, session_id)])


def _invalidate_auth_session() -> None:
    del_auth_cookie()
    del_language_cookie(response)


def _renew_auth_session(username: UserId, session_id: str) -> None:
    _set_auth_cookie(username, session_id)


def _create_auth_session(username: UserId, session_id: str) -> None:
    _set_auth_cookie(username, session_id)


def update_auth_cookie(username: UserId) -> None:
    """Is called during password change to set a new cookie

    We are not able to validate the old cookie value here since the password was already changed
    on the server side. Skip validation in this case, this is fine. The cookie was valdiated
    before accessing this page.
    """
    _set_auth_cookie(username, _get_session_id_from_cookie(username, revalidate_cookie=False))


def _set_auth_cookie(username: UserId, session_id: str) -> None:
    response.set_http_cookie(
        auth_cookie_name(), _auth_cookie_value(username, session_id), secure=request.is_secure
    )


def user_from_cookie(raw_cookie: str) -> Tuple[UserId, str, str]:
    try:
        username, session_id, cookie_hash = raw_cookie.split(":", 2)
    except ValueError:
        raise MKAuthException("Invalid auth cookie.")

    # Refuse pre 2.0 cookies: These held the "issue time" in the 2nd field.
    with suppress(ValueError):
        float(session_id)
        raise MKAuthException("Refusing pre 2.0 auth cookie")

    return UserId(username), session_id, cookie_hash


def _get_session_id_from_cookie(username: UserId, revalidate_cookie: bool) -> str:
    cookie_username, session_id, cookie_hash = user_from_cookie(_fetch_cookie(auth_cookie_name()))

    # Has been checked before, but validate before using that information, just to be sure
    if revalidate_cookie:
        check_parsed_auth_cookie(username, session_id, cookie_hash)

    if cookie_username != username:
        auth_logger.error("Invalid session: (User: %s, Session: %s)", username, session_id)
        return ""

    return session_id


def _renew_cookie(cookie_name: str, username: UserId, session_id: str) -> None:
    # Do not renew if:
    # a) The _ajaxid var is set
    # b) A logout is requested
    requested_file = requested_file_name(request)
    if (
        requested_file != "logout" and not request.has_var("_ajaxid")
    ) and cookie_name == auth_cookie_name():
        auth_logger.debug(
            "Renewing auth cookie (%s.py, vars: %r)" % (requested_file, dict(request.itervars()))
        )
        _renew_auth_session(username, session_id)


def _check_auth_cookie(cookie_name: str) -> Optional[UserId]:
    username, session_id, cookie_hash = user_from_cookie(_fetch_cookie(cookie_name))
    check_parsed_auth_cookie(username, session_id, cookie_hash)

    now = datetime.now()
    try:
        userdb.on_access(username, session_id, now)
    except MKAuthException:
        del_auth_cookie()
        raise

    # Once reached this the cookie is a good one. Renew it!
    _renew_cookie(cookie_name, username, session_id)

    _redirect_for_password_change(username, now)
    _redirect_for_two_factor_authentication(username)

    # Return the authenticated username
    return username


def _redirect_for_password_change(user_id: UserId, now: datetime) -> None:
    if requested_file_name(request) != "user_change_pw":
        if change_reason := userdb.need_to_change_pw(user_id, now):
            raise HTTPRedirect(
                f"user_change_pw.py?_origtarget={urlencode(makeuri(request, []))}&reason={change_reason}"
            )


def _redirect_for_two_factor_authentication(user_id: UserId) -> None:
    if requested_file_name(request) in (
        "user_login_two_factor",
        "user_webauthn_login_begin",
        "user_webauthn_login_complete",
    ):
        return

    if userdb.is_two_factor_login_enabled(user_id) and not userdb.is_two_factor_completed():
        raise HTTPRedirect(
            "user_login_two_factor.py?_origtarget=%s" % urlencode(makeuri(request, []))
        )


def _fetch_cookie(cookie_name: str) -> str:
    raw_cookie = request.cookie(cookie_name, "::")
    assert raw_cookie is not None
    return raw_cookie


def check_parsed_auth_cookie(username: UserId, session_id: str, cookie_hash: str) -> None:
    if not userdb.user_exists(username):
        raise MKAuthException(_("Username is unknown"))

    if cookie_hash != _generate_auth_hash(username, session_id):
        raise MKAuthException(_("Invalid credentials"))


def auth_cookie_is_valid(cookie_text: str) -> bool:
    try:
        check_parsed_auth_cookie(*user_from_cookie(cookie_text))
        return True
    except MKAuthException:
        return False
    except Exception:
        return False


# TODO: Needs to be cleaned up. When using HTTP header auth or web server auth it is not
# ensured that a user exists after letting the user in. This is a problem for the following
# code! We need to define a point where the following code can rely on an existing user
# object. userdb.check_credentials() is doing some similar stuff
# - It also checks the type() of the user_id (Not in the same way :-/)
# - It also calls userdb.is_customer_user_allowed_to_login()
# - It calls userdb.create_non_existing_user() but we don't
# - It calls connection.is_locked() but we don't
def _check_auth(req: Request) -> Optional[UserId]:
    user_id = _check_auth_web_server(req)

    if req.var("_secret"):
        user_id = _check_auth_automation()

    elif auth_by_http_header := active_config.auth_by_http_header:
        if not active_config.user_login:
            return None
        user_id = _check_auth_http_header(auth_by_http_header)

    if user_id is None:
        if not active_config.user_login:
            return None
        user_id = _check_auth_by_cookie()

    if (user_id is not None and not isinstance(user_id, str)) or user_id == "":
        raise MKInternalError(_("Invalid user authentication"))

    if user_id and not userdb.is_customer_user_allowed_to_login(user_id):
        # A CME not assigned with the current sites customer
        # is not allowed to login
        auth_logger.debug("User '%s' is not allowed to authenticate: Invalid customer" % user_id)
        return None

    if user_id and auth_type in ("http_header", "web_server"):
        _check_auth_cookie_for_web_server_auth(user_id)

    return user_id


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
    user_id = request.get_str_input_mandatory("_username", "")

    user_id = UserId(user_id.strip())
    request.del_var_from_env("_username")
    request.del_var_from_env("_secret")

    if verify_automation_secret(user_id, secret):
        # Auth with automation secret succeeded - mark transid as unneeded in this case
        transactions.ignore()
        set_auth_type("automation")
        return user_id
    raise MKAuthException(_("Invalid automation secret for user %s") % user_id)


def _check_auth_http_header(auth_by_http_header: str) -> Optional[UserId]:
    """When http header auth is enabled, try to read the user_id from the var"""
    user_id = request.get_request_header(auth_by_http_header)
    if not user_id:
        return None

    user_id = UserId(user_id)
    set_auth_type("http_header")

    return user_id


def _check_auth_web_server(req: Request) -> Optional[UserId]:
    """Try to get the authenticated user from the HTTP request

    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user.
    """
    # ? type of Request.remote_user attribute is unclear
    user_id = req.remote_user
    if user_id is not None:
        set_auth_type("web_server")
        return UserId(ensure_str(user_id))  # pylint: disable= six-ensure-str-bin-call
    return None


def _check_auth_by_cookie() -> Optional[UserId]:
    cookie_name = auth_cookie_name()
    if not request.has_cookie(cookie_name):
        return None

    try:
        set_auth_type("cookie")
        return _check_auth_cookie(cookie_name)
    except MKAuthException:
        # Suppress cookie validation errors from other sites cookies
        auth_logger.debug(
            "Exception while checking cookie %s: %s" % (cookie_name, traceback.format_exc())
        )
    except Exception:
        auth_logger.debug(
            "Exception while checking cookie %s: %s" % (cookie_name, traceback.format_exc())
        )
    return None


def _check_auth_cookie_for_web_server_auth(user_id: UserId):
    """Session handling also has to be initialized when the authentication is done
    by the web server.

    The authentication is already done on web server level. We accept the provided
    username as authenticated and create our cookie here.
    """
    now = datetime.now()
    if auth_cookie_name() not in request.cookies:
        session_id = userdb.on_succeeded_login(user_id, now)
        _create_auth_session(user_id, session_id)
        return

    # Refresh the existing auth cookie and update the session info
    cookie_name = auth_cookie_name()
    try:
        _check_auth_cookie(cookie_name)
    except MKAuthException:
        # Suppress cookie validation errors from other sites cookies
        auth_logger.debug(
            "Exception while checking cookie %s: %s" % (cookie_name, traceback.format_exc())
        )
    except Exception:
        auth_logger.debug(
            "Exception while checking cookie %s: %s" % (cookie_name, traceback.format_exc())
        )


def set_auth_type(_auth_type: AuthType) -> None:
    request_local_attr().auth_type = _auth_type


auth_type: Union[AuthType, LocalProxy] = LocalProxy(lambda: request_local_attr().auth_type)


@page_registry.register_page("login")
class LoginPage(Page):
    def __init__(self) -> None:
        super().__init__()
        self._no_html_output = False

    def set_no_html_output(self, no_html_output: bool) -> None:
        self._no_html_output = no_html_output

    def page(self) -> None:
        # Initialize the cmk.gui.i18n for the login dialog. This might be
        # overridden later after user login
        cmk.gui.i18n.localize(request.var("lang", active_config.default_language))

        self._do_login()

        if self._no_html_output:
            raise MKAuthException(_("Invalid login credentials."))

        if is_mobile(request, response):
            cmk.gui.mobile.page_login()
            return

        self._show_login_page()

    def _do_login(self) -> None:
        """handle the sent login form"""
        if not request.var("_login"):
            return

        try:
            if not active_config.user_login:
                raise MKUserError(None, _("Login is not allowed on this site."))

            username_var = request.get_str_input("_username", "")
            assert username_var is not None
            username = UserId(username_var.rstrip())
            if not username:
                raise MKUserError("_username", _("Missing username"))

            password = request.var("_password", "")
            if not password:
                raise MKUserError("_password", _("Missing password"))

            default_origtarget = url_prefix() + "check_mk/"
            origtarget = request.get_url_input("_origtarget", default_origtarget)

            # Disallow redirections to:
            #  - logout.py: Happens after login
            #  - side.py: Happens when invalid login is detected during sidebar refresh
            if "logout.py" in origtarget or "side.py" in origtarget:
                origtarget = default_origtarget

            now = datetime.now()
            result = userdb.check_credentials(username, password, now)
            if result:
                # use the username provided by the successful login function, this function
                # might have transformed the username provided by the user. e.g. switched
                # from mixed case to lower case.
                username = result

                session_id = userdb.on_succeeded_login(username, now)

                # The login succeeded! Now:
                # a) Set the auth cookie
                # b) Unset the login vars in further processing
                # c) Redirect to really requested page
                _create_auth_session(username, session_id)

                # Never use inplace redirect handling anymore as used in the past. This results
                # in some unexpected situations. We simpy use 302 redirects now. So we have a
                # clear situation.
                # userdb.need_to_change_pw returns either False or the reason description why the
                # password needs to be changed
                if change_reason := userdb.need_to_change_pw(username, now):
                    raise HTTPRedirect(
                        f"user_change_pw.py?_origtarget={urlencode(origtarget)}&reason={change_reason}"
                    )

                if userdb.is_two_factor_login_enabled(username):
                    raise HTTPRedirect(
                        "user_login_two_factor.py?_origtarget=%s" % urlencode(makeuri(request, []))
                    )

                raise HTTPRedirect(origtarget)

            userdb.on_failed_login(username, now)
            raise MKUserError(None, _("Invalid login"))
        except MKUserError as e:
            user_errors.add(e)

    def _show_login_page(self) -> None:
        html.set_render_headfoot(False)
        html.add_body_css_class("login")
        html.header(get_page_heading(), Breadcrumb(), javascripts=[])

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
        if requested_file_name(request) == "login" and _check_auth(request):
            raise HTTPRedirect(origtarget)

        html.open_div(id_="login")

        html.open_div(id_="login_window")

        html.open_a(href="https://checkmk.com")
        html.img(
            src=theme.detect_icon_path(icon_name="logo", prefix="mk-"),
            id_="logo",
            class_="custom" if theme.has_custom_logo() else None,
        )
        html.close_a()

        html.begin_form("login", method="POST", add_transid=False, action="login.py")
        html.hidden_field("_login", "1")
        html.hidden_field("_origtarget", origtarget)
        html.label("%s:" % _("Username"), id_="label_user", class_=["legend"], for_="_username")
        html.br()
        html.text_input("_username", id_="input_user")
        html.label("%s:" % _("Password"), id_="label_pass", class_=["legend"], for_="_password")
        html.br()
        html.password_input("_password", id_="input_pass", size=None)

        if user_errors:
            html.open_div(id_="login_error")
            html.show_user_errors()
            html.close_div()

        html.open_div(id_="button_text")
        html.button("_login", _("Login"), cssclass="hot")
        html.close_div()
        html.close_div()

        html.open_div(id_="foot")

        if active_config.login_screen.get("login_message"):
            html.open_div(id_="login_message")
            html.show_message(active_config.login_screen["login_message"])
            html.close_div()

        footer: List[HTML] = []
        for title, url, target in active_config.login_screen.get("footer_links", []):
            footer.append(html.render_a(title, href=url, target=target))

        if "hide_version" not in active_config.login_screen:
            footer.append(escape_to_html("Version: %s" % cmk_version.__version__))

        footer.append(
            HTML(
                "&copy; %s"
                % html.render_a("tribe29 GmbH", href="https://tribe29.com", target="_blank")
            )
        )

        html.write_html(HTML(" - ").join(footer))

        if cmk_version.is_raw_edition():
            html.br()
            html.br()
            html.write_text(
                _(
                    'You can use, modify and distribute Check_MK under the terms of the <a href="%s" target="_blank">'
                    "GNU GPL Version 2</a>."
                )
                % "https://checkmk.com/gpl.html"
            )

        html.close_div()

        html.set_focus("_username")
        html.hidden_fields()
        html.end_form()
        html.close_div()

        html.footer()


@page_registry.register_page("logout")
class LogoutPage(Page):
    def page(self) -> None:
        assert user.id is not None

        _invalidate_auth_session()

        session_id = _get_session_id_from_cookie(user.id, revalidate_cookie=True)
        userdb.on_logout(user.id, session_id)

        if auth_type == "cookie":  # type: ignore[has-type]
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
