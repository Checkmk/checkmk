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

import sys
import StringIO
import traceback
from typing import Callable, Dict, List, NamedTuple  # pylint: disable=unused-import

import cmk.gui.config as config
import cmk.gui.i18n
from cmk.gui.i18n import _
from cmk.gui.globals import html

hooks = {}  # type: Dict[str, List[Hook]]

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False


# Load all login plugins
def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    # Cleanup all plugin hooks. They need to be renewed by load_plugins()
    # of the other modules
    unregister_plugin_hooks()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()


def unregister_plugin_hooks():
    old_hooks = hooks.copy()
    for name, registered_hooks in old_hooks.items():
        hooks_left = [h for h in registered_hooks if h.is_builtin]
        if hooks_left:
            hooks[name] = hooks_left
        else:
            del hooks[name]


def register_builtin(name, func):
    register(name, func, is_builtin=True)


def register_from_plugin(name, func):
    register(name, func, is_builtin=False)


Hook = NamedTuple("Hook", [("handler", Callable), ("is_builtin", bool)])


# Kept public for compatibility with pre 1.6 plugins (is_builtin needs to be optional for pre 1.6)
def register(name, func, is_builtin=False):
    hooks.setdefault(name, []).append(Hook(handler=func, is_builtin=is_builtin))


def get(name):
    return hooks.get(name, [])


def registered(name):
    """ Returns True if at least one function is registered for the given hook """
    return hooks.get(name, []) != []


def call(name, *args):
    n = 0
    for hook in hooks.get(name, []):
        n += 1
        try:
            hook.handler(*args)
        except Exception as e:
            if config.debug:
                txt = StringIO.StringIO()
                t, v, tb = sys.exc_info()
                traceback.print_exception(t, v, tb, None, txt)
                html.show_error("<h1>" + _("Error executing hook") + " %s #%d: %s</h1>"
                                "<pre>%s</pre>" % (name, n, e, txt.getvalue()))
            raise
