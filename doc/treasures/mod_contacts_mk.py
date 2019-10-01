#!/usr/bin/python
# This script can be used to modify the contacts.mk file
# The core mus be reloaded after changes
from __future__ import print_function
import sys, os

if len(sys.argv) != 4:
    print("Usage: ./mod_contacts_mk.py USERID FIELD NEW CONTENT")
    sys.exit()
try:
    path = os.environ.pop('OMD_ROOT')
    pathlokal = "~/etc/check_mk/conf.d/wato/"
    pathlokal = os.path.expanduser(pathlokal)
    contacts_mk = pathlokal + "contacts.mk"
except:
    print("Run this script inside a OMD site")
    sys.exit()

user_id = sys.argv[1]
field = sys.argv[2]
content = sys.argv[3]

contacts = {}

eval(open(contacts_mk).read())

contacts[user_id][field] = content

file(contacts_mk, "w").write("""
# Written by Multisite UserDB
# encoding: utf-8

contacts.update(
%s)""" % str(contacts))
