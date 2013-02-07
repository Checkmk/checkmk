#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import defaults, htmllib, config, userdb
from lib import *
from mod_python import apache
import os, time

try:
    from hashlib import md5
except ImportError:
    from md5 import md5 # deprecated with python 2.5

def site_cookie_name(site_id = None):
    if not site_id:
        url_prefix = defaults.url_prefix
    else:
        url_prefix = config.site(site_id)['url_prefix']

    # Strip of eventual present "http://<host>". DIRTY!
    if url_prefix.startswith('http:'):
        url_prefix = url_prefix[url_prefix[7:].find('/') + 7:]

    name = os.path.dirname(url_prefix).replace('/', '_')
    return 'auth%s' % name

# Reads the auth secret from a file. Creates the files if it does
# not exist. Having access to the secret means that one can issue valid
# cookies for the cookie auth.
# FIXME: Secret auch replizieren
def load_secret():
    secret_path = '%s/auth.secret' % os.path.dirname(defaults.htpasswd_file)
    secret = ''
    if os.path.exists(secret_path):
        secret = file(secret_path).read().strip()

    # Create new secret when this installation has no secret
    if secret == '':
        secret = md5(str(time.time())).hexdigest()
        file(secret_path, 'w').write(secret + "\n")

    return secret

# Load the password serial of the user. This serial identifies the current config
# state of the user account. If either the password is changed or the account gets
# locked the serial is increased and all cookies get invalidated.
def load_serial(user_id):
    users = userdb.load_users()
    return users.get(user_id, {}).get('serial', 0)

# Generates the hash to be added into the cookie value
def generate_hash(username, now, serial):
    secret = load_secret()
    return md5(username + now + str(serial) + secret).hexdigest()

def del_auth_cookie():
    name = site_cookie_name()
    if html.has_cookie(name):
        html.del_cookie(name)

def auth_cookie_value(username, serial):
    now = str(time.time())
    return username + ':' + now + ':' + generate_hash(username, now, serial)

def set_auth_cookie(username, serial):
    html.set_cookie(site_cookie_name(), auth_cookie_value(username, serial))

def get_cookie_value():
    return auth_cookie_value(config.user_id, load_serial(config.user_id))

def check_auth_cookie(cookie_name):
    username, issue_time, cookie_hash = html.cookie(cookie_name, '::').split(':', 2)

    # FIXME: Ablauf-Zeit des Cookies testen
    #max_cookie_age = 10
    #if float(issue_time) < time.time() - max_cookie_age:
    #    del_auth_cookie()
    #    return ''

    users = userdb.load_users().keys()
    if not username in users:
        raise MKAuthException(_('Username is unknown'))

    # Validate the hash
    serial = load_serial(username)
    if cookie_hash != generate_hash(username, issue_time, serial):
        raise MKAuthException(_('Invalid credentials'))

    # Once reached this the cookie is a good one. Renew it!
    # Do not renew if:
    # a) The _ajaxid var is set
    # b) A logout is requested
    if (html.req.myfile != 'logout' or html.has_var('_ajaxid')) \
       and cookie_name == site_cookie_name():
        set_auth_cookie(username, serial)

    # Return the authenticated username
    return username

def check_auth_automation():
    secret = html.var("_secret").strip()
    user = html.var("_username").strip()
    del html.req.vars['_username']
    del html.req.vars['_secret']
    if secret and user and "/" not in user:
        path = defaults.var_dir + "/web/" + user + "/automation.secret"
        if os.path.isfile(path) and file(path).read().strip() == secret:
            return user
    raise MKAuthException(_("Invalid automation secret for user %s") % user)

def check_auth():
    if html.var("_secret"):
        return check_auth_automation()

    for cookie_name in html.get_cookie_names():
        if cookie_name.startswith('auth_'):
            try:
                return check_auth_cookie(cookie_name)
            except Exception, e:
                #if html.debug:
                #    html.write('Exception occured while checking cookie %s' % cookie_name)
                #    raise
                #else:
                pass

    return ''


def do_login():
    # handle the sent login form
    err = None
    if html.var('_login'):
        try:
            username = html.var('_username', '').rstrip()
            if username == '':
                raise MKUserError('_username', _('No username given.'))

            password = html.var('_password', '')
            if password == '':
                raise MKUserError('_password', _('No password given.'))

            origtarget = html.var('_origtarget')
            if not origtarget or "logout.py" in origtarget:
                origtarget = defaults.url_prefix + 'check_mk/'

            # None        -> User unknown, means continue with other connectors
            # '<user_id>' -> success
            # False       -> failed
            result = userdb.hook_login(username, password)
            if result:
                username = result
                # The login succeeded! Now:
                # a) Set the auth cookie
                # b) Unset the login vars in further processing
                # c) Show the real requested page (No redirect needed)
                set_auth_cookie(username, load_serial(username))

                # Use redirects for URLs or simply execute other handlers for
                # mulitsite modules
                if '/' in origtarget or '?' in origtarget:
                    html.set_http_header('Location', origtarget)
                    raise apache.SERVER_RETURN, apache.HTTP_MOVED_TEMPORARILY
                else:
                    # Remove login vars to hide them from the next page handler
                    try:
                        del html.req.vars['_username']
                        del html.req.vars['_password']
                        del html.req.vars['_login']
                        del html.req.vars['_origtarget']
                    except:
                        pass

                    return (username, origtarget)
            else:
                raise MKUserError(None, _('Invalid credentials.'))
        except MKUserError, e:
            html.add_user_error(e.varname, e.message)
            return e.message

def page_login(no_html_output = False):
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
    if not origtarget and not html.req.myfile in [ 'login', 'logout' ]:
        origtarget = html.makeuri([])

    # When e.g. the password of a user is changed and the first frame that recognizes the
    # non matching cookies is the sidebar it redirects the user to side.py while removing
    # the frameset. This is not good. Instead of this redirect the user to the index page.
    if html.req.myfile == 'side':
        html.immediate_browser_redirect(0.1, 'login.py')
        return apache.OK

    # Never allow the login page to be opened in a frameset. Redirect top page to login page.
    # This will result in a full screen login page.
    html.javascript('''if(top != self) {
    window.top.location.href = location;
}''')

    # When someone calls the login page directly and is already authed redirect to main page
    if html.req.myfile == 'login' and check_auth() != '':
        html.immediate_browser_redirect(0.5, origtarget and origtarget or 'index.py')
        return apache.OK

    html.write("<div id=login>")
    html.write("<img id=login_window src=\"images/login_window.png\">")
    html.write("<div id=version>%s</div>" % defaults.check_mk_version)

    html.begin_form("login", method = 'POST', add_transid = False)
    html.hidden_field('_login', '1')
    html.hidden_field('_origtarget', htmllib.attrencode(origtarget))
    html.write("<label id=label_user class=legend for=_username>%s:</label><br />" % _('Username'))
    html.text_input("_username", id="input_user")
    html.write("<label id=label_pass class=legend for=_password>%s:</label><br />" % _('Password'))
    html.password_input("_password", id="input_pass", size=None)

    if html.has_user_errors():
        html.write('<div id=login_error>')
        html.show_user_errors()
        html.write('</div>')

    html.write("<div id=button_text>")
    html.image_button("_login", _('Login'))
    html.write("</div>")

    html.write("<div id=foot>Version: %s - &copy; "
               "<a href=\"http://mathias-kettner.de\">Mathias Kettner</a><br><br>" % defaults.check_mk_version)
    html.write(_("You can use, modify and distribute Check_MK under the terms of the <a href='%s'>"
                 "GNU GPL Version 2</a>." % "http://mathias-kettner.de/gpl.html"))
    html.write("</div>")

    html.write("</div>")
    html.set_focus('_username')
    html.hidden_fields()
    html.end_form()

    html.footer()
    return apache.OK

def page_logout():
    # Remove eventual existing cookie
    del_auth_cookie()

    if config.auth_type == 'cookie':
        html.set_http_header('Location', defaults.url_prefix + 'check_mk/login.py')
        raise apache.SERVER_RETURN, apache.HTTP_MOVED_TEMPORARILY
    else:
        # Implement HTTP logout with cookie hack
        if not html.has_cookie('logout'):
            html.set_http_header('WWW-Authenticate', 'Basic realm="%s"' % defaults.nagios_auth_name)
            html.set_cookie('logout', '1')
            raise apache.SERVER_RETURN, apache.HTTP_UNAUTHORIZED
        else:
            html.del_cookie('logout')
            html.set_http_header('Location', defaults.url_prefix + 'check_mk/')
            raise apache.SERVER_RETURN, apache.HTTP_MOVED_TEMPORARILY
