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
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

#!/usr/bin/python
# This script can be used to modify the contacts.mk file
# The core mus be reloaded after changes
import sys, os

if len(sys.argv) != 4:
    print "Usage: ./mod_contacts_mk.py USERID FIELD NEW CONTENT"
    sys.exit()
try:
    path = os.environ.pop('OMD_ROOT')
    pathlokal = "~/etc/check_mk/conf.d/wato/"
    pathlokal = os.path.expanduser(pathlokal)
    contacts_mk = pathlokal + "contacts.mk"
except:
    print "Run this script inside a OMD site"
    sys.exit()


user_id =  sys.argv[1]
field = sys.argv[2]
content = sys.argv[3]

contacts = {}

eval(file(contacts_mk).read())

contacts[user_id][field] = content

file(contacts_mk, "w").write( """
# Written by Multisite UserDB
# encoding: utf-8

contacts.update(
%s)""" % str(contacts))
