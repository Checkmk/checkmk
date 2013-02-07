#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

import config, sys

hooks = {}

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

# Load all login plugins
def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
        return

    # Cleanup all registered hooks. They need to be renewed by load_plugins()
    # of the other modules
    unregister()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language

def unregister():
    global hooks
    hooks = {}

def register(name, func):
    hooks.setdefault(name, []).append(func)

def get(name):
    return hooks.get(name, [])

def registered(name):
    """ Returns True if at least one function is registered for the given hook """
    return hooks.get(name, []) != []

def call(name, *args):
    n = 0
    for hk in hooks.get(name, []):
        n += 1
        try:
            hk(*args)
        except Exception, e:
            if config.debug:
                import traceback, StringIO
                txt = StringIO.StringIO()
                t, v, tb = sys.exc_info()
                traceback.print_exception(t, v, tb, None, txt)
                html.show_error("<h1>" + _("Error executing hook") + " %s #%d: %s</h1>"
                                "<pre>%s</pre>" % (name, n, e, txt.getvalue()))
            raise
