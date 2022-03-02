#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

# TODO: Import errors from passlib are suppressed right now since now
# stub files for mypy are not available.
from passlib.context import CryptContext  # type: ignore[import]
from passlib.hash import bcrypt  # type: ignore[import]

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.type_defs import UserId

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.userdb.utils import (
    CheckCredentialsResult,
    user_connector_registry,
    UserConnector,
)
from cmk.gui.type_defs import UserSpec

crypt_context = CryptContext(
    schemes=[
        "bcrypt",
        # Kept for compatibility with Checkmk < 2.1
        "sha256_crypt",
        # Kept for compatibility with Checkmk < 1.6
        # htpasswd has still md5 as default, also the docs include the "-m" param
        "md5_crypt",
        "apr_md5_crypt",
        "des_crypt",
    ]
)


class Htpasswd:
    """Thin wrapper for loading and saving the htpasswd file"""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path

    def load(self) -> dict[UserId, str]:
        """Loads the contents of a valid htpasswd file into a dictionary and returns the dictionary"""
        entries = {}

        with self._path.open(encoding="utf-8") as f:
            for l in f:
                if ":" not in l:
                    continue

                user_id, pw_hash = l.split(":", 1)
                entries[UserId(user_id)] = pw_hash.rstrip("\n")

        return entries

    def exists(self, user_id: str) -> bool:
        """Whether or not a user exists according to the htpasswd file"""
        return user_id in self.load()

    def save(self, entries: dict[UserId, str]) -> None:
        """Save the dictionary entries (unicode username and hash) to the htpasswd file"""
        output = (
            "\n".join(f"{username}:{hash_}" for username, hash_ in sorted(entries.items())) + "\n"
        )
        store.save_text_to_file("%s" % self._path, output)


# Checkmk supports different authentication frontends for verifying the
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
# - https://httpd.apache.org/docs/2.4/misc/password_encryptions.html
# - https://passlib.readthedocs.io/en/stable/lib/passlib.apache.html
#
def hash_password(password: str) -> str:
    # The rounds aka workfactor should be more than 10
    # it defaults to 12 anyways, but I prefer explicity
    return bcrypt.using(rounds=12).hash(password)


def check_password(password: str, pwhash: str) -> bool:
    try:
        return crypt_context.verify(password, pwhash)
    except ValueError:
        # ValueError("hash could not be identified")
        # Is raised in case of locked users because we prefix the hashes with
        # a "!" sign in this situation.
        return False


@user_connector_registry.register
class HtpasswdUserConnector(UserConnector):
    @classmethod
    def type(cls) -> str:
        return "htpasswd"

    @classmethod
    def title(cls) -> str:
        return _("Apache Local Password File (htpasswd)")

    @classmethod
    def short_title(cls) -> str:
        return _("htpasswd")

    #
    # USERDB API METHODS
    #

    def is_enabled(self) -> bool:
        return True

    def check_credentials(self, user_id: UserId, password: str) -> CheckCredentialsResult:
        users = self._get_htpasswd().load()
        if user_id not in users:
            return None  # not existing user, skip over

        if self._is_automation_user(user_id):
            raise MKUserError(None, _("Automation user rejected"))

        if self._password_valid(users[user_id], password):
            return user_id
        return False

    # ? the exact type of user_id is unclear, str, maybe, based on the line "if user_id not in users" ?
    def _is_automation_user(self, user_id: UserId) -> bool:
        return Path(cmk.utils.paths.var_dir, "web", str(user_id), "automation.secret").is_file()

    def _password_valid(self, pwhash: str, password: str) -> bool:
        return check_password(password, pwhash)

    def save_users(self, users: dict[UserId, UserSpec]) -> None:
        # Apache htpasswd. We only store passwords here. During
        # loading we created entries for all admin users we know. Other
        # users from htpasswd are lost. If you start managing users with
        # WATO, you should continue to do so or stop doing to for ever...
        # Locked accounts get a '!' before their password. This disable it.
        entries = {}

        for uid, user in users.items():
            # only process users which are handled by htpasswd connector
            if user.get("connector", "htpasswd") != "htpasswd":
                continue

            if user.get("password"):
                entries[uid] = "%s%s" % ("!" if user.get("locked", False) else "", user["password"])

        self._get_htpasswd().save(entries)

    def _get_htpasswd(self) -> Htpasswd:
        return Htpasswd(Path(cmk.utils.paths.htpasswd_file))
