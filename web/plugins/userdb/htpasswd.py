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

# API-Specifications:
#
# valid attributes:
#
# id
#   The uniq identifier of the connector
# title
#   The string representing this connector to humans
# login
#   Optional: Hook function can be registered here to be executed
#   to validate a login issued by a user.
#   Gets parameters: username, password
#   Has to return either:
#       '<user_id>' -> Login succeeded
#       False       -> Login failed
#       None        -> Unknown user
# sync
#   Optional: Hook function can be registered here to be executed
#   to synchronize all users.
#   Gets parameters:
# save
#   Optional: Hook function can be registered here to be xecuted
#   to save all users.
#   Gets parameters:
# page
#   Optional: Hook function can be registered here to be xecuted
#   on each call to a multisite page, even on ajax requests etc.
#   Gets parameters:
# locked_attributes
#   List of user attributes locked for all users attached to this
#   connector. Those locked attributes are read-only in WATO.
#   Lockable attributes at the moment:
#     password, locked, roles, contactgroups, alias, email, pager

import crypt
import defaults

# Loads the contents of a valid htpasswd file into a dictionary
# and returns the dictionary
def load_htpasswd():
    creds = {}

    for line in open(defaults.htpasswd_file, 'r'):
        if ':' in line:
            username, pwhash = line.split(':', 1)
            creds[username] = pwhash.rstrip('\n')

    return creds

def encrypt_password(password, salt = None):
    import md5crypt
    if not salt:
        salt = "%06d" % (1000000 * (time.time() % 1.0))
    return md5crypt.md5crypt(password, salt, '$1$')

# Validate hashes taken from the htpasswd file. This method handles
# crypt() and md5 hashes. This should be the common cases in the
# used htpasswd files.
def password_valid(pwhash, password):
    if pwhash[:3] == '$1$':
        salt = pwhash.split('$', 3)[2]
        return pwhash == encrypt_password(password, salt)
    else:
        return pwhash == crypt.crypt(password, pwhash[:2])

# Validates a users credentials
def htpasswd_login(username, password):
    users = load_htpasswd()
    if username not in users:
        return None # not existing user, skip over

    if password_valid(users[username], password):
        return username
    else:
        return False

# Saves htpasswd connector managed users
def htpasswd_save(users):
    # Apache htpasswd. We only store passwords here. During
    # loading we created entries for all admin users we know. Other
    # users from htpasswd are lost. If you start managing users with
    # WATO, you should continue to do so or stop doing to for ever...
    # Locked accounts get a '!' before their password. This disable it.
    out = create_user_file(defaults.htpasswd_file, "w")
    for id, user in users.items():
        # only process users which are handled by htpasswd connector
        if user.get('connector', 'htpasswd') != 'htpasswd':
            continue

        if user.get("password"):
            if user.get("locked", False):
                locksym = '!'
            else:
                locksym = ""
            out.write("%s:%s%s\n" % (id, locksym, user["password"]))

multisite_user_connectors.append({
    'id':          'htpasswd',
    'title':       _('Apache Local Password File (htpasswd)'),
    'short_title': _('htpasswd'),

    # Register hook functions
    'login': htpasswd_login,
    'save':  htpasswd_save,
    # Not registering: sync, locked_attributes, page
})
