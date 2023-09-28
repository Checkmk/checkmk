#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This script can be used to modify the contacts.mk file
# The core mus be reloaded after changes

import os
import sys

if len(sys.argv) != 4:
    print("Usage: ./mod_contacts_mk.py USERID FIELD NEW CONTENT")
    sys.exit()
try:
    path = os.environ.pop("OMD_ROOT")
    pathlokal = "~/etc/check_mk/conf.d/wato/"
    pathlokal = os.path.expanduser(pathlokal)
    contacts_mk = pathlokal + "contacts.mk"
except Exception:
    print("Run this script inside a OMD site")
    sys.exit()

user_id = sys.argv[1]
field = sys.argv[2]
content = sys.argv[3]

contacts = {}

eval(open(contacts_mk).read())

contacts[user_id][field] = content

open(contacts_mk, "w").write(
    """
# Written by Multisite UserDB
# encoding: utf-8

contacts.update(
%s)"""
    % str(contacts)
)
