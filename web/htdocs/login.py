#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2011             mk@mathias-kettner.de |
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

import defaults, htmllib, config
from lib import *
from mod_python import apache
import md5crypt, time

def password_valid(pwhash, password):
    # FIXME: MD5 unterstützen
    import crypt
    #html.write(repr(pwhash + ' ' + crypt.crypt(password, pwhash)))
    return pwhash == crypt.crypt(password, pwhash[:2])

def load_htpasswd():
    creds = {}

    for line in open(defaults.htpasswd_file, 'r'):
        username, pwhash = line.split(':', 1)
        creds[username] = pwhash.rstrip('\n')

    return creds

def generate_hash(username, now, pwhash):
    # FIXME: Secret aus Datei auslesen
    # dirname(defaults.htpasswd_file)
    # FIXME: Datei automatisch erstellen, wenn nicht vorhanden
    # FIXME: Secret auch replizieren
    secret = 'asd'
    return md5crypt.md5crypt(username + now + pwhash, secret)

def del_auth_cookie():
    if html.has_cookie('auth_secret'):
        html.del_cookie('auth_secret')

def set_auth_cookie(username, pwhash):
    now = str(time.time())
    html.set_cookie('auth_secret', username
                                   + ':' + now
                                   + ':' + generate_hash(username, now, pwhash))

def check_auth_cookie():
    username, time, cookie_hash = html.cookie('auth_secret', '').split(':', 2)

    # FIXME: Ablauf-Zeit des Cookies testen

    users = load_htpasswd()
    if not username in users:
        raise Exception
    pwhash = users[username]

    # Validate the hash
    if cookie_hash != generate_hash(username, time, pwhash):
        raise Exception

    # Once reached this the cookie is a good one. Renew it!
    # Do not renew if:
    # a) The _ajaxid var is set
    # b) A logout is requested
    if html.req.myfile != 'logout' or html.has_var('_ajaxid'):
        set_auth_cookie(username, pwhash)

    # Return the authenticated username
    return username


def page():
    # handle the sent login form
    err = None
    if html.var('_login'):
        try:
            username = html.var('_username', '')
            if username == '':
                raise MKUserError('_username', _('No username given.'))

            password = html.var('_password', '')
            if password == '':
                raise MKUserError('_password', _('No password given.'))

            origin = html.var('_origin', defaults.url_prefix + 'check_mk/')

            users = load_htpasswd()
            if username in users and password_valid(users[username], password):
                # The login succeeded! Now:
                # a) Set the auth cookie
                # b) Unset the login vars in further processing
                # c) Show the real requested page (No redirect needed)
                set_auth_cookie(username, users[username])

                # Remove login vars to hide them from the next page handler
                del html.req.vars['_username']
                del html.req.vars['_password']
                del html.req.vars['_login']
                del html.req.vars['_origin']

                return (username, origin)
                # An alternative (and maybe cleaner) would be to use a redirect here:
                #html.set_http_header('Location', html.var('_origin', defaults.url_prefix + 'check_mk/'))
                #return apache.HTTP_MOVED_TEMPORARILY
            else:
                raise MKUserError(None, _('Invalid credentials.'))
        except MKUserError, e:
            err = e
            html.add_user_error(e.varname, e.message)

    html.header(_("Check_MK Multisite Login"), add_js = False)

    if err:
        html.write('<div class=error>%s</div>\n' % e.message)

    html.write("<table id=table_login>")
    html.write("<tr class=form>\n")
    html.write("<td>")
    html.begin_form("login", method = 'POST', add_transid = False)
    html.hidden_field('_origin', htmllib.attrencode(html.req.uri))
    html.write("<div class=whiteborder>\n")
    html.write("<table class=\"form\">\n")

    html.write("<tr>")
    html.write("<td class=legend>%s</td>" % _('Username'))
    html.write("<td class=content>")
    html.text_input("_username", size = 50)
    html.write("</td>")
    html.write("</tr>")

    html.write("<tr>")
    html.write("<td class=legend>%s</td>" % _('Password'))
    html.write("<td class=content>")
    html.password_input("_password", size = 50)
    html.write("</td>")
    html.write("</tr>")

    html.write("<tr>")
    html.write("<td colspan=2 class=legend>")
    html.button("_login", _('Login'))
    html.write("</td>")
    html.write("</tr>")

    html.write("</table></div>")
    html.set_focus('_username')
    html.end_form()

    html.footer()
    return apache.OK

def check_auth():
    try:
        if not html.has_cookie('auth_secret'):
            return ''

        return check_auth_cookie()
    except Exception, e:
        return ''

def logout():
    # Remove eventual existing cookie
    del_auth_cookie()

    if config.auth_type == 'cookie':
        html.set_http_header('Location', defaults.url_prefix + 'check_mk/')
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
