#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

from lib import *
import time

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

# Load all login plugins
def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
        return

    # declare & initialize global vars
    global multisite_user_connectors ; multisite_user_connectors = []

    load_web_plugins("userdb", globals())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language

def list_user_connectors():
    return [ (c['id'], c['title']) for c in multisite_user_connectors ]

# This is a function needed in WATO and the htpasswd module. This should
# really be modularized one day. Till this day this is a good place ...
def encrypt_password(password, salt = None):
    import md5crypt
    if not salt:
        salt = "%06d" % (1000000 * (time.time() % 1.0))
    return md5crypt.md5crypt(password, salt, '$1$')

def hook_login(username, password):
    for connector in multisite_user_connectors:
        handler = connector.get('login', None)
        if handler:
            result = handler(username, password)
            # None -> User unknown, means continue with other connectors
            if result != None:
                return result # is True (success) or False (login failed)
