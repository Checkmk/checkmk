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

import time
import crypt
import os

import cmk.store as store
import cmk.paths

import cmk.gui.md5crypt
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError
from . import UserConnector, user_connector_registry

def encrypt_password(password, salt=None, prefix="1"):
    if not salt:
        salt = "%06d" % (1000000 * (time.time() % 1.0))
    return cmk.gui.md5crypt.md5crypt(password, salt, '$%s$' % prefix)


@user_connector_registry.register
class HtpasswdUserConnector(UserConnector):
    @classmethod
    def type(cls):
        return 'htpasswd'


    @classmethod
    def title(cls):
        return _('Apache Local Password File (htpasswd)')


    @classmethod
    def short_title(cls):
        return _('htpasswd')


    #
    # USERDB API METHODS
    #

    def check_credentials(self, user_id, password):
        users = self.load_htpasswd()
        if user_id not in users:
            return None # not existing user, skip over

        if self._is_automation_user(user_id):
            raise MKUserError(None, _("Automation user rejected"))

        if self.password_valid(users[user_id], password):
            return user_id
        return False


    def _is_automation_user(self, user_id):
        return os.path.isfile(cmk.paths.var_dir + "/web/" + user_id.encode("utf-8") + "/automation.secret")


    # Loads the contents of a valid htpasswd file into a dictionary
    # and returns the dictionary
    def load_htpasswd(self):
        creds = {}

        for line in open(cmk.paths.htpasswd_file, 'r'):
            if ':' in line:
                user_id, pwhash = line.split(':', 1)
                creds[user_id.decode("utf-8")] = pwhash.rstrip('\n')

        return creds


    # Validate hashes taken from the htpasswd file. This method handles
    # crypt() and md5 hashes. This should be the common cases in the
    # used htpasswd files.
    def password_valid(self, pwhash, password):
        if pwhash.startswith('$1$') or pwhash.startswith('$apr1$'):
            prefix, salt = pwhash.split('$', 3)[1:3]
            return pwhash == encrypt_password(password, salt, prefix)
        return pwhash == crypt.crypt(password, pwhash[:2])


    def save_users(self, users):
        # Apache htpasswd. We only store passwords here. During
        # loading we created entries for all admin users we know. Other
        # users from htpasswd are lost. If you start managing users with
        # WATO, you should continue to do so or stop doing to for ever...
        # Locked accounts get a '!' before their password. This disable it.
        output = ""

        for id, user in users.items():
            # only process users which are handled by htpasswd connector
            if user.get('connector', 'htpasswd') != 'htpasswd':
                continue

            if user.get("password"):
                if user.get("locked", False):
                    locksym = '!'
                else:
                    locksym = ""
                output += "%s:%s%s\n" % (id.encode("utf-8"), locksym, user["password"])

        store.save_file(cmk.paths.htpasswd_file, output)
