#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from typing import Dict, Text  # pylint: disable=unused-import
import six

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # pylint: disable=import-error,unused-import

# TODO: Import errors from passlib are suppressed right now since now
# stub files for mypy are not available.
from passlib.context import CryptContext  # type: ignore[import]
from passlib.hash import sha256_crypt  # type: ignore[import]

import cmk.utils.paths
import cmk.utils.store as store
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _

from . import UserConnector, user_connector_registry

crypt_context = CryptContext(schemes=[
    "sha256_crypt",
    # Kept for compatibility with Check_MK < 1.6
    "md5_crypt",
    "apr_md5_crypt",
    "des_crypt",
])


class Htpasswd(object):
    """Thin wrapper for loading and saving the htpasswd file"""
    def __init__(self, path):
        # type: (Path) -> None
        super(Htpasswd, self).__init__()
        self._path = path

    def load(self):
        # type: () -> Dict[Text, Text]
        """Loads the contents of a valid htpasswd file into a dictionary and returns the dictionary"""
        entries = {}

        with self._path.open(encoding="utf-8") as f:
            for l in f:
                if ':' not in l:
                    continue

                user_id, pw_hash = l.split(':', 1)
                entries[user_id] = pw_hash.rstrip('\n')

        return entries

    def exists(self, user_id):
        # type: (Text) -> bool
        """Whether or not a user exists according to the htpasswd file"""
        return user_id in self.load()

    def save(self, entries):
        # type: (Dict[Text, Text]) -> None
        """Save the dictionary entries (unicode username and hash) to the htpasswd file"""
        output = "\n".join("%s:%s" % entry for entry in sorted(entries.items())) + "\n"
        store.save_text_to_file("%s" % self._path, output)


# Check_MK supports different authentication frontends for verifying the
# local credentials:
#
# a) basic authentication
# b) GUI form + cookie based authentication
#
# The default is b). This option is toggled with the "omd config" option
# MULTISITE_COOKIE_AUTH. In case the basic authentication is chosen it
# is only possible use hashing algorithms that are supported by the
# web server which performs the authentication.
#
# See:
# - https://httpd.apache.org/docs/2.2/misc/password_encryptions.html
# - https://httpd.apache.org/docs/2.4/misc/password_encryptions.html
# - https://passlib.readthedocs.io/en/stable/lib/passlib.apache.html
#
# For best compatibility in all mentioned situations we use the sha256_crypt
# scheme.
def hash_password(password):
    return sha256_crypt.hash(password)


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

    def is_enabled(self):
        return True

    def check_credentials(self, user_id, password):
        users = self._get_htpasswd().load()
        if user_id not in users:
            return None  # not existing user, skip over

        if self._is_automation_user(user_id):
            raise MKUserError(None, _("Automation user rejected"))

        if self._password_valid(users[user_id], password):
            return user_id
        return False

    def _is_automation_user(self, user_id):
        return os.path.isfile(cmk.utils.paths.var_dir + "/web/" + six.ensure_str(user_id) +
                              "/automation.secret")

    # Validate hashes taken from the htpasswd file. For the moment this function
    # needs to be able to deal with des_crypt and apr-md5 hashes which were used
    # by installations till Check_MK 1.6. The current algorithm also needs to be
    # handled: sha256_crypt.
    def _password_valid(self, pwhash, password):
        try:
            return crypt_context.verify(password, pwhash)
        except ValueError:
            # ValueError("hash could not be identified")
            # Is raised in case of locked users because we prefix the hashes with
            # a "!" sign in this situation.
            return False

    def save_users(self, users):
        # Apache htpasswd. We only store passwords here. During
        # loading we created entries for all admin users we know. Other
        # users from htpasswd are lost. If you start managing users with
        # WATO, you should continue to do so or stop doing to for ever...
        # Locked accounts get a '!' before their password. This disable it.
        entries = {}

        for uid, user in users.items():
            # only process users which are handled by htpasswd connector
            if user.get('connector', 'htpasswd') != 'htpasswd':
                continue

            if user.get("password"):
                entries[uid] = "%s%s" % \
                    ("!" if user.get("locked", False) else "", user["password"])

        self._get_htpasswd().save(entries)

    def _get_htpasswd(self):
        return Htpasswd(Path(cmk.utils.paths.htpasswd_file))
