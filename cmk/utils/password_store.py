#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module is meant to be used by components (e.g. active checks, notifications, bakelets)
that support getting credentials from the Check_MK password store.

The password stores primary use is to centralize stored credentials. Instead of spreading the
credentials in the whole configuration, we have this as a central place for sensitive information.

The password store mechanic provides a mechanism for keeping passwords out of the cmdline of a
process, e.g. an active check plugin. It has been built to extend existing plugins with as small
modificiations as possible. It is built out of two parts:

a) Adding arguments for the command line. This job is done for active checks plugins by
   `cmk.base.core_config._prepare_check_command` and `cmk.base.check_api.passwordstore_get_cmdline`.

b) Extracting arguments from the command line. This is done by `password_store.replace_passwords`
   for python plugins and for C monitoring plugins by the patches which can be found at
   `omd/packages/monitoring-plugins/patches/0003-cmk-password-store.dif`.

   The most interesting part is, that the password store arguments are replaced before the existing
   argument handling of the active check plugins is executed. This way we don't have to deal with
   the individual mechanics of the active check plugins. We can hook into the entry point of the
   plugin, do our work and leave the rest to the plugin.

Python active check plugins need to do something like this before the argv are processed.

  import cmk.utils.password_store
  cmk.utils.password_store.replace_passwords()

  (... use regular argv processing ...)

For cases where the password ID is not received from the command line, for example a configuration
file, there is the `extract` function which can be used like this:

  import cmk.utils.password_store
  password = cmk.utils.password_store.extract("pw_id")

"""

import secrets
import shutil
import string
import sys
from contextlib import suppress
from pathlib import Path
from typing import Literal, Mapping, NoReturn, Optional, TypedDict, Union

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.config_path import ConfigPath, LATEST_CONFIG
from cmk.utils.encryption import Encrypter
from cmk.utils.exceptions import MKGeneralException

PasswordLookupType = Literal["password", "store"]
PasswordId = Union[str, tuple[PasswordLookupType, str]]
Password = TypedDict(
    "Password",
    {
        "title": str,
        "comment": str,
        "docu_url": str,
        "password": str,
        # Only owners can edit the password
        # None -> Administrators (having the permission "Write access to all passwords")
        # str -> Name of the contact group owning the password
        "owned_by": Optional[str],
        "shared_with": list[str],
    },
)


def password_store_path() -> Path:
    return Path(cmk.utils.paths.var_dir, "stored_passwords")


def bail_out(s: str) -> NoReturn:
    sys.stdout.write("UNKNOWN - %s\n" % s)
    sys.stderr.write("UNKNOWN - %s\n" % s)
    sys.exit(3)


def replace_passwords() -> None:
    if len(sys.argv) < 2:
        return  # command line too short

    if not [a for a in sys.argv if a.startswith("--pwstore")]:
        return  # no password store in use

    # --pwstore=4@4@web,6@0@foo
    #  In the 4th argument at char 4 replace the following bytes
    #  with the passwords stored under the ID 'web'
    #  In the 6th argument at char 0 insert the password with the ID 'foo'

    # Extract first argument and parse it

    pwstore_args = sys.argv.pop(1).split("=", 1)[1]
    passwords = load_for_helpers()

    for password_spec in pwstore_args.split(","):
        parts = password_spec.split("@")
        if len(parts) != 3:
            bail_out("pwstore: Invalid --pwstore entry: %s" % password_spec)

        try:
            num_arg, pos_in_arg, password_id = int(parts[0]), int(parts[1]), parts[2]
        except ValueError:
            bail_out("pwstore: Invalid format: %s" % password_spec)

        try:
            arg = sys.argv[num_arg]
        except IndexError:
            bail_out("pwstore: Argument %d does not exist" % num_arg)

        try:
            password = passwords[password_id]
        except KeyError:
            bail_out("pwstore: Password '%s' does not exist" % password_id)

        sys.argv[num_arg] = arg[:pos_in_arg] + password + arg[pos_in_arg + len(password) :]


def save(stored_passwords: Mapping[str, str]) -> None:
    """Save the passwords to the pre-activation path"""
    content = ""
    for ident, pw in stored_passwords.items():
        content += "%s:%s\n" % (ident, pw)

    store.save_bytes_to_file(password_store_path(), _obfuscate(content))


def load() -> dict[str, str]:
    return _load(password_store_path())


def _load(store_path: Path) -> dict[str, str]:
    passwords = {}
    with suppress(FileNotFoundError):
        for line in _deobfuscate(store_path.read_bytes()).splitlines():
            ident, password = line.strip().split(":", 1)
            passwords[ident] = password
    return passwords


def extract(password_id: PasswordId) -> Optional[str]:
    if not isinstance(password_id, tuple):
        return load().get(password_id)

    # In case we get a tuple, assume it was coming from a ValueSpec "PasswordFromStore"
    pw_type, pw_id = password_id
    if pw_type == "password":
        return pw_id
    if pw_type == "store":
        # TODO: Is this None really intended? Shouldn't we better raise an exception?
        return load().get(pw_id)

    raise MKGeneralException("Unknown password type.")


def save_for_helpers(config_base_path: ConfigPath) -> None:
    """Save the passwords for the helpers of the monitoring core"""
    helper_path = _helper_password_store_path(config_base_path)
    helper_path.parent.mkdir(parents=True, exist_ok=True)
    with suppress(OSError):
        shutil.copy(password_store_path(), helper_path)


def load_for_helpers() -> dict[str, str]:
    return _load(_helper_password_store_path(LATEST_CONFIG))


def _helper_password_store_path(config_path: ConfigPath) -> Path:
    return Path(config_path) / "stored_passwords"


class _PasswordStoreObfuscater(Encrypter):
    """Encrypt the password store with the locally known password store key

    But why?

    We are a monitoring system. We definitely need credentials in clear text to contact remote some
    systems all the time. And we also need to be able do this after restarting the whole system.
    This means the secrets need to be available to the site user on disk in clear text.

    To underline this fact, we kept the password store file in clear text on disk for a long time.
    This approach made the situation clearly visible to everyone. And we were pretty comfortable
    with this.

    We are faced with the requirement that no credential shall be stored in clear text on disk, they
    need to be encrypted. We'd love to have that too. But since securing is not possible, we are now
    obfuscating. The best we can do in this case.

    "Sometimes people don't want to hear the truth because they don't want their illusions
    destroyed." - Friedrich Nietzsche

    What we do from now is:

    a) Use a locally stored secret accessible to the site user.
    b) Encrypt the password store which is also accessible to the site user.

    Obviously there is no added security here. Just obfuscation.

    Sorry. But this is the way it is.

    With the development of Checkmk 2.2 we will evaluate the usage of HSMs as well
    as vault solutions in the future which may be helpful in some use cases.

    PS. If you think this is all nonsense and you have a secure solution to this situation, I am
    very interested in learning from you.
    """

    VERSION = 0
    VERSION_BYTE_LENGTH = 2

    @classmethod
    def _secret_key_path(cls) -> Path:
        path = cmk.utils.paths.omd_root / "etc" / "password_store.secret"
        if not path.exists():
            # Initialize the password store encryption key in case it does not exist
            cls._create_secret_key(path)
        return path

    @classmethod
    def _create_secret_key(cls, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        path.chmod(0o660)
        path.write_text(
            "".join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(256))
        )

    @classmethod
    def encrypt(cls, value: str) -> bytes:
        return cls.VERSION.to_bytes(cls.VERSION_BYTE_LENGTH, byteorder="big") + super().encrypt(
            value
        )

    @classmethod
    def decrypt(cls, raw: bytes) -> str:
        return super().decrypt(raw[cls.VERSION_BYTE_LENGTH :])


_obfuscate = _PasswordStoreObfuscater.encrypt
_deobfuscate = _PasswordStoreObfuscater.decrypt
