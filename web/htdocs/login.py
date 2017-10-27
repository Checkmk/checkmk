#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import config
import userdb
from lib import *
from log import logger
from html_mod_python import FinalizeRequest
import os
import time
import traceback
import i18n
from hashlib import md5

import cmk.paths

auth_type = None
auth_logger = logger.getChild("auth")

# Perform the user authentication. This is called by index.py to ensure user
# authentication and initialization of the user related data structures.
#
# Initialize the user session with the mod_python provided request object.
# The user may have configured (basic) authentication by the web server. In
# case a user is provided, we trust that user and assume it as authenticated.
#
# Otherwise we check / ask for the cookie authentication or eventually the
# automation secret authentication.
def authenticate(mod_python_req):
    # Check whether or not already authenticated
    user_id = check_auth(mod_python_req)
    if user_id:
        login(user_id)
        return True
    else:
        return False


# After the user has been authenticated, tell the different components
# of the GUI which user is authenticated.
def login(user_id):
    if type(user_id) != unicode:
        raise MKInternalError("Invalid user id type")
    config.set_user_by_id(user_id)
    html.set_user_id(user_id)


def auth_cookie_name():
    return 'auth%s' % site_cookie_suffix()


def site_cookie_suffix():
    url_prefix = config.url_prefix()

    # Strip of eventual present "http://<host>". DIRTY!
    if url_prefix.startswith('http:'):
        url_prefix = url_prefix[url_prefix[7:].find('/') + 7:]

    return os.path.dirname(url_prefix).replace('/', '_')

# Reads the auth secret from a file. Creates the files if it does
# not exist. Having access to the secret means that one can issue valid
# cookies for the cookie auth.
def load_secret():
    secret_path = '%s/auth.secret' % os.path.dirname(cmk.paths.htpasswd_file)
    secret = ''
    if os.path.exists(secret_path):
        secret = file(secret_path).read().strip()

    # Create new secret when this installation has no secret
    #
    # In past versions we used another bad approach to generate a secret. This
    # checks for such secrets and creates a new one. This will invalidate all
    # current auth cookies which means that all logged in users will need to
    # renew their login after update.
    if secret == '' or len(secret) == 32:
        secret = generate_secret()
        file(secret_path, 'w').write(secret)

    return secret

def generate_secret():
    return get_random_string(256)

# Load the password serial of the user. This serial identifies the current config
# state of the user account. If either the password is changed or the account gets
# locked the serial is increased and all cookies get invalidated.
# Better use the value from the "serials.mk" file, instead of loading the whole
# user database via load_users() for performance reasons.
def load_serial(username):
    return userdb.load_custom_attr(username, 'serial', saveint, 0)


def generate_auth_hash(username, now):
    return generate_hash(username, username.encode("utf-8") + str(now))


# Generates a hash to be added into the cookie value
def generate_hash(username, value):
    secret = load_secret()
    serial = load_serial(username)
    return md5(value + str(serial) + secret).hexdigest()


def del_auth_cookie():
    # Note: in distributed setups a cookie issued by one site is accepted by
    # others with the same auth.secret and user serial numbers. When a users
    # logs out then we need to delete all cookies that are accepted by us -
    # not just the one that we have issued.
    for cookie_name in html.get_cookie_names():
        if cookie_name.startswith("auth_"):
            if auth_cookie_is_valid(cookie_name):
                html.del_cookie(cookie_name)


def auth_cookie_value(username):
    now = str(time.time())
    return ":".join([ username, now, generate_auth_hash(username, now) ])


def invalidate_auth_session():
    if config.single_user_session != None:
        userdb.invalidate_session(config.user.id)

    del_auth_cookie()
    i18n.del_language_cookie()


def renew_auth_session(username):
    if config.single_user_session != None:
        userdb.refresh_session(username)

    set_auth_cookie(username)


def create_auth_session(username):
    if config.single_user_session != None:
        session_id = userdb.initialize_session(username)
        set_session_cookie(username, session_id)

    set_auth_cookie(username)


def set_auth_cookie(username):
    html.set_cookie(auth_cookie_name(), auth_cookie_value(username))


def set_session_cookie(username, session_id):
    html.set_cookie(session_cookie_name(), session_cookie_value(username, session_id))


def session_cookie_name():
    return 'session%s' % site_cookie_suffix()


def session_cookie_value(username, session_id):
    value = username.encode("utf-8") + ":" + session_id
    return value + ":" + generate_hash(username, value)


def get_session_id_from_cookie(username):
    raw_value = html.cookie(session_cookie_name(), "::")
    cookie_username, session_id, cookie_hash = raw_value.split(':', 2)

    if cookie_username.decode("utf-8") != username \
       or cookie_hash != generate_hash(username, username.encode("utf-8") + ":" + session_id):
        auth_logger.error("Invalid session: %s, Cookie: %r" % (username, raw_value))
        return ""

    return session_id


def renew_cookie(cookie_name, username):
    # Do not renew if:
    # a) The _ajaxid var is set
    # b) A logout is requested
    if (html.myfile != 'logout' and not html.has_var('_ajaxid')) \
       and cookie_name == auth_cookie_name():
        auth_logger.debug("Renewing auth cookie (%s.py, vars: %r)" % (html.myfile, html.vars))
        renew_auth_session(username)


def check_auth_cookie(cookie_name):
    username, issue_time, cookie_hash = parse_auth_cookie(cookie_name)
    check_parsed_auth_cookie(username, issue_time, cookie_hash)

    # Check whether or not there is an idle timeout configured, delete cookie and
    # require the user to renew the log when the timeout exceeded.
    if userdb.login_timed_out(username, issue_time):
        del_auth_cookie()
        return

    # Check whether or not a single user session is allowed at a time and the user
    # is doing this request with the currently active session.
    if config.single_user_session != None:
        session_id = get_session_id_from_cookie(username)
        if not userdb.is_valid_user_session(username, session_id):
            del_auth_cookie()
            return

    # Once reached this the cookie is a good one. Renew it!
    renew_cookie(cookie_name, username)

    if html.myfile != 'user_change_pw':
        result = userdb.need_to_change_pw(username)
        if result:
            html.http_redirect('user_change_pw.py?_origtarget=%s&reason=%s' % (html.urlencode(html.makeuri([])), result))

    # Return the authenticated username
    return username


def parse_auth_cookie(cookie_name):
    raw_value = html.cookie(cookie_name, "::")
    username, issue_time, cookie_hash = raw_value.split(':', 2)
    return username.decode("utf-8"), float(issue_time), cookie_hash


def check_parsed_auth_cookie(username, issue_time, cookie_hash):
    if not userdb.user_exists(username):
        raise MKAuthException(_('Username is unknown'))

    if cookie_hash != generate_auth_hash(username, issue_time):
        raise MKAuthException(_('Invalid credentials'))


def auth_cookie_is_valid(cookie_name):
    try:
        check_parsed_auth_cookie(*parse_auth_cookie(cookie_name))
        return True
    except MKAuthException:
        return False
    except Exception:
        log_exception()
        return False


def check_auth(mod_python_req):
    user_id = check_auth_web_server(mod_python_req)

    if html.var("_secret"):
        user_id = check_auth_automation()

    elif config.auth_by_http_header:
        user_id = check_auth_http_header()

    if user_id is None:
        user_id = check_auth_by_cookie()

    if (user_id is not None and type(user_id) != unicode) or user_id == u'':
        raise MKInternalError(_("Invalid user authentication"))

    if user_id and not userdb.is_customer_user_allowed_to_login(user_id):
        # A CME not assigned with the current sites customer
        # is not allowed to login
        auth_logger.debug("User '%s' is not allowed to authenticate: Invalid customer" % user_id)
        return None

    return user_id


def check_auth_automation():
    secret = html.var("_secret").strip()
    user_id = html.get_unicode_input("_username").strip()
    html.del_var('_username')
    html.del_var('_secret')
    if secret and user_id and "/" not in user_id:
        path = cmk.paths.var_dir + "/web/" + user_id.encode("utf-8") + "/automation.secret"
        if os.path.isfile(path) and file(path).read().strip() == secret:
            # Auth with automation secret succeeded - mark transid as unneeded in this case
            html.set_ignore_transids()
            set_auth_type("automation")
            return user_id
    raise MKAuthException(_("Invalid automation secret for user %s") % user_id)


# When http header auth is enabled, try to read the user_id from the var
# and when there is some available, set the auth cookie (for other addons) and proceed.
def check_auth_http_header():
    user_id = html.get_request_header(config.auth_by_http_header)
    if not user_id:
        return None

    user_id = user_id.decode("utf-8")
    set_auth_type("http_header")
    renew_cookie(auth_cookie_name(), user_id)
    return user_id


# Try to get the authenticated user from the mod_python provided request object.
# The user may have configured (basic) authentication by the web server. In
# case a user is provided, we trust that user.
def check_auth_web_server(mod_python_req):
    if mod_python_req.user != None:
        set_auth_type("web_server")
        return mod_python_req.user.decode("utf-8")


def check_auth_by_cookie():
    for cookie_name in html.get_cookie_names():
        if cookie_name.startswith('auth_'):
            try:
                set_auth_type("cookie")
                return check_auth_cookie(cookie_name)
            except MKAuthException:
                # Suppress cookie validation errors from other sites cookies
                auth_logger.debug('Exception while checking cookie %s: %s' %
                                        (cookie_name, traceback.format_exc()))
            except Exception, e:
                auth_logger.error('Exception while checking cookie %s: %s' %
                                    (cookie_name, traceback.format_exc()))


def set_auth_type(ty):
    global auth_type
    auth_type = ty


def do_login():
    # handle the sent login form
    if html.var('_login'):
        try:
            username = html.get_unicode_input('_username', '').rstrip()
            if username == '':
                raise MKUserError('_username', _('No username given.'))

            password = html.var('_password', '')
            if password == '':
                raise MKUserError('_password', _('No password given.'))

            origtarget = html.var('_origtarget')
            # Disallow redirections to:
            #  - logout.py: Happens after login
            #  - side.py: Happens when invalid login is detected during sidebar refresh
            #  - Full qualified URLs (http://...) to prevent redirection attacks
            if not origtarget or "logout.py" in origtarget or 'side.py' in origtarget or '://' in origtarget:
                origtarget = config.url_prefix() + 'check_mk/'

            # None        -> User unknown, means continue with other connectors
            # '<user_id>' -> success
            # False       -> failed
            result = userdb.hook_login(username, password)
            if result:
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
                create_auth_session(username)

                # Never use inplace redirect handling anymore as used in the past. This results
                # in some unexpected situations. We simpy use 302 redirects now. So we have a
                # clear situation.
                # userdb.need_to_change_pw returns either False or the reason description why the
                # password needs to be changed
                result = userdb.need_to_change_pw(username)
                if result:
                    html.http_redirect('user_change_pw.py?_origtarget=%s&reason=%s' % (html.urlencode(origtarget), result))
                else:
                    html.http_redirect(origtarget)
            else:
                userdb.on_failed_login(username)
                raise MKUserError(None, _('Invalid credentials.'))
        except MKUserError, e:
            html.add_user_error(e.varname, e)
            return "%s" % e

def page_login(no_html_output = False):
    # Initialize the i18n for the login dialog. This might be overridden
    # later after user login
    i18n.localize(html.var("lang", config.get_language()))

    result = do_login()
    if type(result) == tuple:
        return result # Successful login
    elif no_html_output:
        raise MKAuthException(_("Invalid login credentials."))

    if html.mobile:
        import mobile
        return mobile.page_login()

    else:
        return normal_login_page()

def normal_login_page(called_directly = True):
    html.set_render_headfoot(False)
    html.header(_("Check_MK Multisite Login"), javascripts=[], stylesheets=["pages", "login"])

    origtarget = html.var('_origtarget', '')
    if not origtarget and not html.myfile in [ 'login', 'logout' ]:
        origtarget = html.makeuri([])

    # Never allow the login page to be opened in a frameset. Redirect top page to login page.
    # This will result in a full screen login page.
    html.javascript('''if(top != self) {
    window.top.location.href = location;
}''')

    # When someone calls the login page directly and is already authed redirect to main page
    if html.myfile == 'login' and check_auth(html.req):
        html.http_redirect(origtarget and origtarget or 'index.py')

    html.open_div(id_="login")
    html.open_div(id_="login_window")
    html.div(cmk.__version__, id_="version")

    html.begin_form("login", method = 'POST', add_transid = False, action = 'login.py')
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
    html.write("Version: %s - &copy; " % cmk.__version__)
    html.a("Mathias Kettner", href="https://mathias-kettner.com")
    html.br()
    html.br()
    html.write(_('You can use, modify and distribute Check_MK under the terms of the <a href="%s">'
                 'GNU GPL Version 2</a>.') % "https://mathias-kettner.com/gpl.html")
    html.close_div()

    html.set_focus('_username')
    html.hidden_fields()
    html.end_form()
    html.close_div()

    html.footer()

def page_logout():
    invalidate_auth_session()

    if auth_type == 'cookie':
        html.http_redirect(config.url_prefix() + 'check_mk/login.py')
    else:
        # Implement HTTP logout with cookie hack
        if not html.has_cookie('logout'):
            html.set_http_header('WWW-Authenticate', 'Basic realm="OMD Monitoring Site %s"' % config.omd_site())
            html.set_cookie('logout', '1')
            raise FinalizeRequest(401)
        else:
            html.del_cookie('logout')
            html.http_redirect(config.url_prefix() + 'check_mk/')
