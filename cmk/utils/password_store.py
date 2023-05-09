#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module is meant to be used by components (e.g. active checks, notifications, bakelets)
that support getting credentials from the Check_MK password store.

The module needs to be included and then the script needs to run the
replace_passwords() function. This should be done early in the script
to make the pwstore option handling transparent for the script.

Do it like this:

  import cmk.utils.password_store
  cmk.utils.password_store.replace_passwords()

"""

import sys

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException

password_store_path = cmk.utils.paths.var_dir + "/stored_passwords"


def bail_out(s):
    sys.stdout.write("UNKNOWN - %s\n" % s)
    sys.exit(3)


def replace_passwords():
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
    passwords = load()

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

        sys.argv[num_arg] = arg[:pos_in_arg] \
                            + password \
                            + arg[pos_in_arg + len(password):]


def save(stored_passwords):
    content = ""
    for ident, pw in stored_passwords.items():
        content += "%s:%s\n" % (ident, pw["password"])

    store.save_file(password_store_path, content)


def load():
    passwords = {}
    for line in open(password_store_path):
        ident, password = line.strip().split(":", 1)
        passwords[ident] = password
    return passwords


def extract(password_id):

    if not isinstance(password_id, tuple):
        return load().get(password_id)

    # In case we get a tuple, assume it was coming from a ValueSpec "PasswordFromStore"
    pw_type, pw_id = password_id
    if pw_type == "password":
        return pw_id
    if pw_type == "store":
        return load().get(pw_id)

    raise MKGeneralException("Unknown password type.")
