#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client
import os
import traceback
import contextlib
from hashlib import sha256
from typing import List, Union, Optional, Tuple, Iterator
from pathlib import Path
from contextlib import suppress

from six import ensure_binary, ensure_str
from werkzeug.local import LocalProxy

import cmk.utils.version as cmk_version
import cmk.utils.paths
from cmk.utils.type_defs import UserId

import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.utils as utils
from cmk.gui.log import logger
import cmk.gui.i18n
import cmk.gui.mobile
from cmk.gui.http import Request
from cmk.gui.pages import page_registry, Page
from cmk.gui.i18n import _
from cmk.gui.globals import html, local, request as global_request
from cmk.gui.htmllib import HTML
from cmk.gui.breadcrumb import Breadcrumb

from cmk.gui.exceptions import HTTPRedirect, MKInternalError, MKAuthException, MKUserError, FinalizeRequest

from cmk.gui.utils.urls import makeuri

auth_logger = logger.getChild("auth")


@contextlib.contextmanager
def authenticate(request: Request) -> Iterator[bool]:
    """Perform the user authentication

    This is called by index.py to ensure user
    authentication and initialization of the user related data structures.

    Initialize the user session with the mod_python provided request object.
    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user and assume it as authenticated.

    Otherwise we check / ask for the cookie authentication or eventually the
    automation secret authentication."""

    user_id = _check_auth(request)
    if not user_id:
        yield False
        return

    with UserSessionContext(user_id):
        yield True


@contextlib.contextmanager
def UserSessionContext(user_id: UserId) -> Iterator[None]:
    """Managing context of authenticated user session with cleanup before logout."""
    with config.UserContext(user_id):
        try:
            yield
        finally:
            html.transaction_manager.store_new()
            userdb.on_end_of_request(user_id)


def auth_cookie_name() -> str:
    return 'auth%s' % site_cookie_suffix()


def site_cookie_suffix() -> str:
    url_prefix = config.url_prefix()

    # Strip of eventual present "http://<host>". DIRTY!
    if url_prefix.startswith('http:'):
        url_prefix = url_prefix[url_prefix[7:].find('/') + 7:]

    return os.path.dirname(url_prefix).replace('/', '_')


def _load_secret() -> str:
    """Reads the sites auth secret from a file

    Creates the files if it does not exist. Having access to the secret means that one can issue
    valid cookies for the cookie auth.
    """
    htpasswd_path = Path(cmk.utils.paths.htpasswd_file)
    secret_path = htpasswd_path.parent.joinpath('auth.secret')

    secret = u''
    if secret_path.exists():
        with secret_path.open(encoding="utf-8") as f:
            secret = f.read().strip()

    # Create new secret when this installation has no secret
    #
    # In past versions we used another bad approach to generate a secret. This
    # checks for such secrets and creates a new one. This will invalidate all
    # current auth cookies which means that all logged in users will need to
    # renew their login after update.
    if secret == '' or len(secret) == 32:
        secret = _generate_secret()
        with secret_path.open("w", encoding="utf-8") as f:
            f.write(secret)

    return secret


def _generate_secret() -> str:
    return ensure_str(utils.get_random_string(256))


def _load_serial(username: UserId) -> int:
    """Load the password serial of the user

    This serial identifies the current config state of the user account. If either the password is
    changed or the account gets locked the serial is increased and all cookies get invalidated.
    Better use the value from the "serials.mk" file, instead of loading the whole user database via
    load_users() for performance reasons.
    """
    return userdb.load_custom_attr(username, 'serial', int, 0)


def _generate_auth_hash(username: UserId, session_id: str) -> str:
    return _generate_hash(username, ensure_str(username) + session_id)


def _generate_hash(username: UserId, value: str) -> str:
    """Generates a hash to be added into the cookie value"""
    secret = _load_secret()
    serial = _load_serial(username)
    return sha256(ensure_binary(value + str(serial) + secret)).hexdigest()


def del_auth_cookie() -> None:
    cookie_name = auth_cookie_name()
    if not html.request.has_cookie(cookie_name):
        return

    cookie = _fetch_cookie(cookie_name)
    if auth_cookie_is_valid(cookie):
        html.response.delete_cookie(cookie_name)


def _auth_cookie_value(username: UserId, session_id: str) -> str:
    return ":".join([ensure_str(username), session_id, _generate_auth_hash(username, session_id)])


def _invalidate_auth_session() -> None:
    del_auth_cookie()
    html.del_language_cookie()


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
    html.response.set_http_cookie(auth_cookie_name(), _auth_cookie_value(username, session_id))


def user_from_cookie(raw_cookie: str) -> Tuple[UserId, str, str]:
    try:
        username, session_id, cookie_hash = raw_cookie.split(':', 2)
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
    if (html.myfile != 'logout' and not html.request.has_var('_ajaxid')) \
       and cookie_name == auth_cookie_name():
        auth_logger.debug("Renewing auth cookie (%s.py, vars: %r)" %
                          (html.myfile, dict(html.request.itervars())))
        _renew_auth_session(username, session_id)


def _check_auth_cookie(cookie_name: str) -> Optional[UserId]:
    username, session_id, cookie_hash = user_from_cookie(_fetch_cookie(cookie_name))
    check_parsed_auth_cookie(username, session_id, cookie_hash)

    try:
        userdb.on_access(username, session_id)
    except MKAuthException:
        del_auth_cookie()
        raise

    # Once reached this the cookie is a good one. Renew it!
    _renew_cookie(cookie_name, username, session_id)

    if html.myfile != 'user_change_pw':
        result = userdb.need_to_change_pw(username)
        if result:
            raise HTTPRedirect('user_change_pw.py?_origtarget=%s&reason=%s' %
                               (html.urlencode(makeuri(global_request, [])), result))

    # Return the authenticated username
    return username


def _fetch_cookie(cookie_name: str) -> str:
    raw_cookie = html.request.cookie(cookie_name, "::")
    assert raw_cookie is not None
    return raw_cookie


def check_parsed_auth_cookie(username: UserId, session_id: str, cookie_hash: str) -> None:
    if not userdb.user_exists(username):
        raise MKAuthException(_('Username is unknown'))

    if cookie_hash != _generate_auth_hash(username, session_id):
        raise MKAuthException(_('Invalid credentials'))


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
def _check_auth(request: Request) -> Optional[UserId]:
    user_id = _check_auth_web_server(request)

    if html.request.var("_secret"):
        user_id = _check_auth_automation()

    elif config.auth_by_http_header:
        if not config.user_login:
            return None
        user_id = _check_auth_http_header()

    if user_id is None:
        if not config.user_login and not _is_site_login():
            return None
        user_id = _check_auth_by_cookie()

    if (user_id is not None and not isinstance(user_id, str)) or user_id == u'':
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
        path = Path(cmk.utils.paths.var_dir) / "web" / ensure_str(user_id) / "automation.secret"
        if not path.is_file():
            return False

        with path.open(encoding="utf-8") as f:
            return ensure_str(f.read()).strip() == secret

    return False


def _check_auth_automation() -> UserId:
    secret = html.request.get_str_input_mandatory("_secret", "").strip()
    user_id = html.request.get_unicode_input_mandatory("_username", "")

    user_id = UserId(user_id.strip())
    html.del_var_from_env('_username')
    html.del_var_from_env('_secret')

    if verify_automation_secret(user_id, secret):
        # Auth with automation secret succeeded - mark transid as unneeded in this case
        html.transaction_manager.ignore()
        set_auth_type("automation")
        return user_id
    raise MKAuthException(_("Invalid automation secret for user %s") % user_id)


def _check_auth_http_header() -> Optional[UserId]:
    """When http header auth is enabled, try to read the user_id from the var"""
    assert isinstance(config.auth_by_http_header, str)
    user_id = html.request.get_request_header(config.auth_by_http_header)
    if not user_id:
        return None

    user_id = UserId(ensure_str(user_id))
    set_auth_type("http_header")

    return user_id


def _check_auth_web_server(request: Request) -> Optional[UserId]:
    """Try to get the authenticated user from the HTTP request

    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user.
    """
    user = request.remote_user
    if user is not None:
        set_auth_type("web_server")
        return UserId(ensure_str(user))
    return None


def _check_auth_by_cookie() -> Optional[UserId]:
    cookie_name = auth_cookie_name()
    if not html.request.has_cookie(cookie_name):
        return None

    try:
        set_auth_type("cookie")
        return _check_auth_cookie(cookie_name)
    except MKAuthException:
        # Suppress cookie validation errors from other sites cookies
        auth_logger.debug('Exception while checking cookie %s: %s' %
                          (cookie_name, traceback.format_exc()))
    except Exception:
        auth_logger.debug('Exception while checking cookie %s: %s' %
                          (cookie_name, traceback.format_exc()))
    return None


def _check_auth_cookie_for_web_server_auth(user_id: UserId):
    """Session handling also has to be initialized when the authentication is done
    by the web server.

    The authentication is already done on web server level. We accept the provided
    username as authenticated and create our cookie here.
    """
    if auth_cookie_name() not in html.request.cookies:
        session_id = userdb.on_succeeded_login(user_id)
        _create_auth_session(user_id, session_id)
        return

    # Refresh the existing auth cookie and update the session info
    cookie_name = auth_cookie_name()
    try:
        _check_auth_cookie(cookie_name)
    except MKAuthException:
        # Suppress cookie validation errors from other sites cookies
        auth_logger.debug('Exception while checking cookie %s: %s' %
                          (cookie_name, traceback.format_exc()))
    except Exception:
        auth_logger.debug('Exception while checking cookie %s: %s' %
                          (cookie_name, traceback.format_exc()))


def set_auth_type(_auth_type: str) -> None:
    local.auth_type = _auth_type


auth_type: Union[str, LocalProxy] = LocalProxy(lambda: local.auth_type)


@page_registry.register_page("login")
class LoginPage(Page):
    def __init__(self) -> None:
        super(LoginPage, self).__init__()
        self._no_html_output = False

    def set_no_html_output(self, no_html_output: bool) -> None:
        self._no_html_output = no_html_output

    def page(self) -> None:
        # Initialize the cmk.gui.i18n for the login dialog. This might be
        # overridden later after user login
        cmk.gui.i18n.localize(html.request.var("lang", config.get_language()))

        self._do_login()

        if self._no_html_output:
            raise MKAuthException(_("Invalid login credentials."))

        if html.mobile:
            cmk.gui.mobile.page_login()
            return

        self._show_login_page()

    def _do_login(self) -> None:
        """handle the sent login form"""
        if not html.request.var('_login'):
            return

        try:
            if not config.user_login and not _is_site_login():
                raise MKUserError(None, _('Login is not allowed on this site.'))

            username_var = html.request.get_unicode_input('_username', '')
            assert username_var is not None
            username = UserId(username_var.rstrip())
            if not username:
                raise MKUserError('_username', _('No username given.'))

            password = html.request.var('_password', '')
            if not password:
                raise MKUserError('_password', _('No password given.'))

            default_origtarget = config.url_prefix() + "check_mk/"
            origtarget = html.get_url_input("_origtarget", default_origtarget)

            # Disallow redirections to:
            #  - logout.py: Happens after login
            #  - side.py: Happens when invalid login is detected during sidebar refresh
            if "logout.py" in origtarget or 'side.py' in origtarget:
                origtarget = default_origtarget

            result = userdb.check_credentials(username, password)
            if result:
                # use the username provided by the successful login function, this function
                # might have transformed the username provided by the user. e.g. switched
                # from mixed case to lower case.
                username = result

                session_id = userdb.on_succeeded_login(username)

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
                change_pw_result = userdb.need_to_change_pw(username)
                if change_pw_result:
                    raise HTTPRedirect('user_change_pw.py?_origtarget=%s&reason=%s' %
                                       (html.urlencode(origtarget), change_pw_result))
                raise HTTPRedirect(origtarget)

            userdb.on_failed_login(username)
            raise MKUserError(None, _('Invalid credentials.'))
        except MKUserError as e:
            html.add_user_error(e.varname, e)

    def _show_login_page(self) -> None:
        html.set_render_headfoot(False)
        html.add_body_css_class("login")
        html.header(config.get_page_heading(), Breadcrumb(), javascripts=[])

        default_origtarget = ("index.py" if html.myfile in ["login", "logout"] else makeuri(
            global_request, []))
        origtarget = html.get_url_input("_origtarget", default_origtarget)

        # Never allow the login page to be opened in the iframe. Redirect top page to login page.
        # This will result in a full screen login page.
        html.javascript('''if(top != self) {
    window.top.location.href = location;
}''')

        # When someone calls the login page directly and is already authed redirect to main page
        if html.myfile == 'login' and _check_auth(html.request):
            raise HTTPRedirect(origtarget)

        html.open_div(id_="login")

        html.open_div(id_="login_window")

        html.img(src=html.detect_icon_path(icon_name="logo", prefix="mk-"),
                 id_="logo",
                 class_="custom" if config.has_custom_logo() else None)

        html.begin_form("login", method='POST', add_transid=False, action='login.py')
        html.hidden_field('_login', '1')
        html.hidden_field('_origtarget', origtarget)
        html.label("%s:" % _('Username'), id_="label_user", class_=["legend"], for_="_username")
        html.br()
        html.text_input("_username", id_="input_user")
        html.label("%s:" % _('Password'), id_="label_pass", class_=["legend"], for_="_password")
        html.br()
        html.password_input("_password", id_="input_pass", size=None)

        if html.has_user_errors():
            html.open_div(id_="login_error")
            html.show_user_errors()
            html.close_div()

        html.open_div(id_="button_text")
        html.button("_login", _('Login'), cssclass="hot")
        html.close_div()
        html.close_div()

        html.open_div(id_="foot")

        if config.login_screen.get("login_message"):
            html.open_div(id_="login_message")
            html.show_message(config.login_screen["login_message"])
            html.close_div()

        footer: List[Union[HTML, str]] = []
        for title, url, target in config.login_screen.get("footer_links", []):
            footer.append(html.render_a(title, href=url, target=target))

        if "hide_version" not in config.login_screen:
            footer.append("Version: %s" % cmk_version.__version__)

        footer.append("&copy; %s" %
                      html.render_a("tribe29 GmbH", href="https://checkmk.com", target="_blank"))

        html.write(HTML(" - ").join(footer))

        if cmk_version.is_raw_edition():
            html.br()
            html.br()
            html.write(
                _('You can use, modify and distribute Check_MK under the terms of the <a href="%s" target="_blank">'
                  'GNU GPL Version 2</a>.') % "https://checkmk.com/gpl.html")

        html.close_div()

        html.set_focus('_username')
        html.hidden_fields()
        html.end_form()
        html.close_div()

        html.footer()


def _is_site_login() -> bool:
    """Determine if login is a site login for connecting central and remote
    site. This login has to be allowed even if site login on remote site is not
    permitted by rule "Direct login to Web GUI allowed" """
    if html.myfile == "login":
        if (origtarget_var := html.request.var("_origtarget")) is None:
            return False
        return (origtarget_var.startswith("automation_login.py") and
                "_version=" in origtarget_var and "_edition_short=" in origtarget_var)

    if html.myfile == "automation_login":
        return bool(html.request.var("_edition_short") and html.request.var("_version"))

    return False


@page_registry.register_page("logout")
class LogoutPage(Page):
    def page(self) -> None:
        assert config.user.id is not None

        _invalidate_auth_session()

        session_id = _get_session_id_from_cookie(config.user.id, revalidate_cookie=True)
        userdb.on_logout(config.user.id, session_id)

        if auth_type == 'cookie':
            raise HTTPRedirect(config.url_prefix() + 'check_mk/login.py')

        # Implement HTTP logout with cookie hack
        if not html.request.has_cookie('logout'):
            html.response.headers['WWW-Authenticate'] = ('Basic realm="OMD Monitoring Site %s"' %
                                                         config.omd_site())
            html.response.set_http_cookie('logout', '1')
            raise FinalizeRequest(http.client.UNAUTHORIZED)

        html.response.delete_cookie('logout')
        raise HTTPRedirect(config.url_prefix() + 'check_mk/')
