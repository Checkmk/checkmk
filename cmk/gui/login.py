#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import time
import traceback
import sys
from hashlib import md5
from typing import Union, Tuple, Optional, Text  # pylint: disable=unused-import

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import six
from werkzeug.local import LocalProxy

import cmk.utils.paths
from cmk.utils.encoding import ensure_unicode
from cmk.utils.type_defs import UserId

import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.utils as utils
from cmk.gui.log import logger
import cmk.gui.i18n
import cmk.gui.mobile
from cmk.gui.http import Request  # pylint: disable=unused-import
from cmk.gui.pages import page_registry, Page
from cmk.gui.i18n import _
from cmk.gui.globals import html, local
from cmk.gui.htmllib import HTML

from cmk.gui.exceptions import HTTPRedirect, MKInternalError, MKAuthException, MKUserError, FinalizeRequest

auth_logger = logger.getChild("auth")


def authenticate(request):
    # type: (Request) -> bool
    """Perform the user authentication

    This is called by index.py to ensure user
    authentication and initialization of the user related data structures.

    Initialize the user session with the mod_python provided request object.
    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user and assume it as authenticated.

    Otherwise we check / ask for the cookie authentication or eventually the
    automation secret authentication."""
    # Check whether or not already authenticated
    user_id = _check_auth(request)
    if user_id:
        login(user_id)
        return True
    return False


def login(user_id):
    # type: (UserId) -> None
    """After the user has been authenticated, tell the different components
    of the GUI which user is authenticated."""
    config.set_user_by_id(user_id)


def auth_cookie_name():
    # type: () -> str
    return 'auth%s' % site_cookie_suffix()


def site_cookie_suffix():
    # type: () -> str
    url_prefix = config.url_prefix()

    # Strip of eventual present "http://<host>". DIRTY!
    if url_prefix.startswith('http:'):
        url_prefix = url_prefix[url_prefix[7:].find('/') + 7:]

    return os.path.dirname(url_prefix).replace('/', '_')


def _load_secret():
    # type: () -> Text
    """Reads the sites auth secret from a file

    Creates the files if it does not exist. Having access to the secret means that one can issue
    valid cookies for the cookie auth.
    """
    htpasswd_path = Path(cmk.utils.paths.htpasswd_file)
    secret_path = htpasswd_path.parent.joinpath('auth.secret')

    secret = u''
    if secret_path.exists():  # pylint: disable=no-member
        with secret_path.open(encoding="utf-8") as f:  # pylint: disable=no-member
            secret = f.read().strip()

    # Create new secret when this installation has no secret
    #
    # In past versions we used another bad approach to generate a secret. This
    # checks for such secrets and creates a new one. This will invalidate all
    # current auth cookies which means that all logged in users will need to
    # renew their login after update.
    if secret == '' or len(secret) == 32:
        secret = _generate_secret()
        with secret_path.open("w", encoding="utf-8") as f:  # pylint: disable=no-member
            f.write(secret)

    return secret


def _generate_secret():
    # type: () -> Text
    return ensure_unicode(utils.get_random_string(256))


def _load_serial(username):
    # type: (UserId) -> int
    """Load the password serial of the user

    This serial identifies the current config state of the user account. If either the password is
    changed or the account gets locked the serial is increased and all cookies get invalidated.
    Better use the value from the "serials.mk" file, instead of loading the whole user database via
    load_users() for performance reasons.
    """
    return userdb.load_custom_attr(username, 'serial', int, 0)


def _generate_auth_hash(username, now):
    # type: (UserId, float) -> str
    return _generate_hash(username, six.ensure_str(username) + str(now))


def _generate_hash(username, value):
    # type: (UserId, str) -> str
    """Generates a hash to be added into the cookie value"""
    secret = _load_secret()
    serial = _load_serial(username)
    return md5(six.ensure_binary(value + str(serial) + secret)).hexdigest()


def del_auth_cookie():
    # type: () -> None
    # Note: in distributed setups a cookie issued by one site is accepted by
    # others with the same auth.secret and user serial numbers. When a users
    # logs out then we need to delete all cookies that are accepted by us -
    # not just the one that we have issued.
    for cookie_name in html.request.get_cookie_names():
        if cookie_name.startswith("auth_"):
            if _auth_cookie_is_valid(cookie_name):
                html.response.delete_cookie(cookie_name)


def _auth_cookie_value(username):
    # type: (UserId) -> str
    now = time.time()
    return ":".join([six.ensure_str(username), str(now), _generate_auth_hash(username, now)])


def _invalidate_auth_session():
    # type: () -> None
    if config.single_user_session is not None:
        userdb.invalidate_session(config.user.id)

    del_auth_cookie()
    html.del_language_cookie()


def _renew_auth_session(username):
    # type: (UserId) -> None
    if config.single_user_session is not None:
        userdb.refresh_session(username)

    set_auth_cookie(username)


def _create_auth_session(username):
    # type: (UserId) -> None
    if config.single_user_session is not None:
        session_id = userdb.initialize_session(username)
        _set_session_cookie(username, session_id)

    set_auth_cookie(username)


def set_auth_cookie(username):
    # type: (UserId) -> None
    html.response.set_http_cookie(auth_cookie_name(), _auth_cookie_value(username))


def _set_session_cookie(username, session_id):
    # type: (UserId, str) -> None
    html.response.set_http_cookie(_session_cookie_name(),
                                  _session_cookie_value(username, session_id))


def _session_cookie_name():
    # type: () -> str
    return 'session%s' % site_cookie_suffix()


def _session_cookie_value(username, session_id):
    # type: (UserId, str) -> str
    value = six.ensure_str(username) + ":" + session_id
    return value + ":" + _generate_hash(username, value)


def _get_session_id_from_cookie(username):
    # type: (UserId) -> str
    raw_value = html.request.cookie(_session_cookie_name(), "::")
    cookie_username, session_id, cookie_hash = raw_value.split(':', 2)

    if ensure_unicode(cookie_username) != username \
       or cookie_hash != _generate_hash(username, username + ":" + session_id):
        auth_logger.error("Invalid session: %s, Cookie: %r" % (username, raw_value))
        return ""

    return session_id


def _renew_cookie(cookie_name, username):
    # type: (str, UserId) -> None
    # Do not renew if:
    # a) The _ajaxid var is set
    # b) A logout is requested
    if (html.myfile != 'logout' and not html.request.has_var('_ajaxid')) \
       and cookie_name == auth_cookie_name():
        auth_logger.debug("Renewing auth cookie (%s.py, vars: %r)" %
                          (html.myfile, dict(html.request.itervars())))
        _renew_auth_session(username)


def _check_auth_cookie(cookie_name):
    # type: (str) -> Optional[UserId]
    username, issue_time, cookie_hash = _parse_auth_cookie(cookie_name)
    _check_parsed_auth_cookie(username, issue_time, cookie_hash)

    # Check whether or not there is an idle timeout configured, delete cookie and
    # require the user to renew the log when the timeout exceeded.
    if userdb.login_timed_out(username, issue_time):
        del_auth_cookie()
        return None

    # Check whether or not a single user session is allowed at a time and the user
    # is doing this request with the currently active session.
    if config.single_user_session is not None:
        session_id = _get_session_id_from_cookie(username)
        if not userdb.is_valid_user_session(username, session_id):
            del_auth_cookie()
            return None

    # Once reached this the cookie is a good one. Renew it!
    _renew_cookie(cookie_name, username)

    if html.myfile != 'user_change_pw':
        result = userdb.need_to_change_pw(username)
        if result:
            raise HTTPRedirect('user_change_pw.py?_origtarget=%s&reason=%s' %
                               (html.urlencode(html.makeuri([])), result))

    # Return the authenticated username
    return username


def _parse_auth_cookie(cookie_name):
    # type: (str) -> Tuple[UserId, float, str]
    raw_value = ensure_unicode(html.request.cookie(cookie_name, b"::"))
    username, issue_time, cookie_hash = raw_value.split(':', 2)
    return UserId(username), float(issue_time) if issue_time else 0.0, six.ensure_str(cookie_hash)


def _check_parsed_auth_cookie(username, issue_time, cookie_hash):
    # type: (UserId, float, str) -> None
    if not userdb.user_exists(username):
        raise MKAuthException(_('Username is unknown'))

    if cookie_hash != _generate_auth_hash(username, issue_time):
        raise MKAuthException(_('Invalid credentials'))


def _auth_cookie_is_valid(cookie_name):
    # type: (str) -> bool
    try:
        _check_parsed_auth_cookie(*_parse_auth_cookie(cookie_name))
        return True
    except MKAuthException:
        return False
    except Exception:
        return False


# TODO: Needs to be cleaned up. When using HTTP header auth or web server auth it is not
# ensured that a user exists after letting the user in. This is a problem for the following
# code! We need to define a point where the following code can rely on an existing user
# object. userdb.hook_login() is doing some similar stuff
# - It also checks the type() of the user_id (Not in the same way :-/)
# - It also calls userdb.is_customer_user_allowed_to_login()
# - It calls userdb.create_non_existing_user() but we don't
# - It calls connection.is_locked() but we don't
def _check_auth(request):
    # type: (Request) -> Optional[UserId]
    user_id = check_auth_web_server(request)  # type: Optional[UserId]

    if html.request.var("_secret"):
        user_id = _check_auth_automation()

    elif config.auth_by_http_header:
        user_id = _check_auth_http_header()

    if user_id is None:
        user_id = _check_auth_by_cookie()

    if (user_id is not None and not isinstance(user_id, six.text_type)) or user_id == u'':
        raise MKInternalError(_("Invalid user authentication"))

    if user_id and not userdb.is_customer_user_allowed_to_login(user_id):
        # A CME not assigned with the current sites customer
        # is not allowed to login
        auth_logger.debug("User '%s' is not allowed to authenticate: Invalid customer" % user_id)
        return None

    return user_id


def verify_automation_secret(user_id, secret):
    # type: (UserId, str) -> bool
    if secret and user_id and "/" not in user_id:
        path = cmk.utils.paths.var_dir + "/web/" + six.ensure_str(user_id) + "/automation.secret"
        if not os.path.isfile(path):
            return False

        with open(path) as f:
            return f.read().strip() == secret

    return False


def _check_auth_automation():
    # type: () -> UserId
    secret = html.request.var("_secret", "").strip()
    user_id = html.request.get_unicode_input("_username", "")
    assert isinstance(user_id, six.text_type)

    user_id = UserId(user_id.strip())
    html.del_var_from_env('_username')
    html.del_var_from_env('_secret')

    if verify_automation_secret(user_id, secret):
        # Auth with automation secret succeeded - mark transid as unneeded in this case
        html.transaction_manager.ignore()
        set_auth_type("automation")
        return user_id
    raise MKAuthException(_("Invalid automation secret for user %s") % user_id)


def _check_auth_http_header():
    # type: () -> Optional[UserId]
    """When http header auth is enabled, try to read the user_id from the var
    and when there is some available, set the auth cookie (for other addons) and proceed."""
    user_id = html.request.get_request_header(config.auth_by_http_header)
    if not user_id:
        return None

    user_id = UserId(ensure_unicode(user_id))
    set_auth_type("http_header")
    _renew_cookie(auth_cookie_name(), user_id)
    return user_id


def check_auth_web_server(request):
    # type: (Request) -> UserId
    """Try to get the authenticated user from the HTTP request

    The user may have configured (basic) authentication by the web server. In
    case a user is provided, we trust that user.
    """
    user = request.remote_user
    if user is not None:
        set_auth_type("web_server")
        return UserId(ensure_unicode(user))


def _check_auth_by_cookie():
    # type: () -> Optional[UserId]
    for cookie_name in html.request.get_cookie_names():
        if cookie_name.startswith('auth_'):
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


def set_auth_type(_auth_type):
    # type: (str) -> None
    local.auth_type = _auth_type


auth_type = LocalProxy(lambda: local.auth_type)  # type: Union[str, LocalProxy]


@page_registry.register_page("login")
class LoginPage(Page):
    def __init__(self):
        # type: () -> None
        super(LoginPage, self).__init__()
        self._no_html_output = False

    def set_no_html_output(self, no_html_output):
        # type: (bool) -> None
        self._no_html_output = no_html_output

    def page(self):
        # type: () -> None
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

    def _do_login(self):
        # type: () -> None
        """handle the sent login form"""
        if not html.request.var('_login'):
            return

        try:
            username_var = html.request.get_unicode_input('_username', '')
            assert username_var is not None
            username = UserId(username_var.rstrip())
            if username == '':
                raise MKUserError('_username', _('No username given.'))

            password = html.request.var('_password', '')
            if password == '':
                raise MKUserError('_password', _('No password given.'))

            default_origtarget = config.url_prefix() + "check_mk/"
            origtarget = html.get_url_input("_origtarget", default_origtarget)

            # Disallow redirections to:
            #  - logout.py: Happens after login
            #  - side.py: Happens when invalid login is detected during sidebar refresh
            if "logout.py" in origtarget or 'side.py' in origtarget:
                origtarget = default_origtarget

            # '<user_id>' -> success
            # False       -> failed
            result = userdb.hook_login(username, password)
            if result:
                assert isinstance(result, six.text_type)
                # use the username provided by the successful login function, this function
                # might have transformed the username provided by the user. e.g. switched
                # from mixed case to lower case.
                username = result

                # When single user session mode is enabled, check that there is not another
                # active session
                userdb.ensure_user_can_init_session(username)

                # reset failed login counts
                userdb.on_succeeded_login(username)

                # The login succeeded! Now:
                # a) Set the auth cookie
                # b) Unset the login vars in further processing
                # c) Redirect to really requested page
                _create_auth_session(username)

                # Never use inplace redirect handling anymore as used in the past. This results
                # in some unexpected situations. We simpy use 302 redirects now. So we have a
                # clear situation.
                # userdb.need_to_change_pw returns either False or the reason description why the
                # password needs to be changed
                change_pw_result = userdb.need_to_change_pw(username)
                if change_pw_result:
                    raise HTTPRedirect('user_change_pw.py?_origtarget=%s&reason=%s' %
                                       (html.urlencode(origtarget), change_pw_result))
                else:
                    raise HTTPRedirect(origtarget)
            else:
                userdb.on_failed_login(username)
                raise MKUserError(None, _('Invalid credentials.'))
        except MKUserError as e:
            html.add_user_error(e.varname, e)

    def _show_login_page(self):
        # type: () -> None
        html.set_render_headfoot(False)
        html.add_body_css_class("login")
        html.header(config.get_page_heading(), javascripts=[])

        default_origtarget = "index.py" if html.myfile in ["login", "logout"] else html.makeuri([])
        origtarget = html.get_url_input("_origtarget", default_origtarget)

        # Never allow the login page to be opened in a frameset. Redirect top page to login page.
        # This will result in a full screen login page.
        html.javascript('''if(top != self) {
    window.top.location.href = location;
}''')

        # When someone calls the login page directly and is already authed redirect to main page
        if html.myfile == 'login' and _check_auth(html.request):
            raise HTTPRedirect(origtarget)

        html.open_div(id_="login")

        html.open_div(id_="login_window")

        html.div("" if "hide_version" in config.login_screen else cmk.__version__, id_="version")

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
        html.button("_login", _('Login'))
        html.close_div()
        html.close_div()

        html.open_div(id_="foot")

        if config.login_screen.get("login_message"):
            html.open_div(id_="login_message")
            html.show_message(config.login_screen["login_message"])
            html.close_div()

        footer = []
        for title, url, target in config.login_screen.get("footer_links", []):
            footer.append(html.render_a(title, href=url, target=target))

        if "hide_version" not in config.login_screen:
            footer.append("Version: %s" % cmk.__version__)

        footer.append("&copy; %s" %
                      html.render_a("tribe29 GmbH", href="https://checkmk.com", target="_blank"))

        html.write(HTML(" - ").join(footer))

        if cmk.is_raw_edition():
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


@page_registry.register_page("logout")
class LogoutPage(Page):
    def page(self):
        # type: () -> None
        _invalidate_auth_session()

        if auth_type == 'cookie':
            raise HTTPRedirect(config.url_prefix() + 'check_mk/login.py')
        else:
            # Implement HTTP logout with cookie hack
            if not html.request.has_cookie('logout'):
                html.response.headers[
                    'WWW-Authenticate'] = 'Basic realm="OMD Monitoring Site %s"' % config.omd_site(
                    )
                html.response.set_http_cookie('logout', '1')
                raise FinalizeRequest(six.moves.http_client.UNAUTHORIZED)
            else:
                html.response.delete_cookie('logout')
                raise HTTPRedirect(config.url_prefix() + 'check_mk/')
