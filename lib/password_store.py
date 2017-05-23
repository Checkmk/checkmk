#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

"""This module is meant to be used by active checks that support getting
credentials from the Check_MK password store.

The module needs to be included and then the script needs to run the
replace_passwords() function. This should be done early in the script
to make the pwstore option handling transparent for the script.

Do it like this:

  import cmk.password_store
  cmk.password_store.replace_passwords()

"""

import sys

import cmk.paths
import cmk.store as store

password_store_path = cmk.paths.var_dir + "/stored_passwords"

def bail_out(s):
    sys.stdout.write("UNKNOWN - %s\n" % s)
    sys.exit(3)


def replace_passwords():
    if len(sys.argv) < 2:
        return # command line too short

    if not [ a for a in sys.argv if a.startswith("--pwstore")  ]:
        return # no password store in use

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
                          + arg[pos_in_arg+len(password):]


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
