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

import config
import lib
import re

def ajax_tree_openclose():
    html.load_tree_states()

    tree = html.var("tree")
    name = html.get_unicode_input("name")

    if not tree or not name:
        raise lib.MKUserError(None, _('tree or name parameter missing'))

    html.set_tree_state(tree, name, html.var("state"))
    html.save_tree_states()
    html.write('OK') # Write out something to make debugging easier

#   .--Row Selector--------------------------------------------------------.
#   |      ____                 ____       _           _                   |
#   |     |  _ \ _____      __ / ___|  ___| | ___  ___| |_ ___  _ __       |
#   |     | |_) / _ \ \ /\ / / \___ \ / _ \ |/ _ \/ __| __/ _ \| '__|      |
#   |     |  _ < (_) \ V  V /   ___) |  __/ |  __/ (__| || (_) | |         |
#   |     |_| \_\___/ \_/\_/   |____/ \___|_|\___|\___|\__\___/|_|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Saves and loads selected row information of the current user         |
#   +----------------------------------------------------------------------+

import os, time
from lib import make_nagios_directory

def init_selection():
    # Generate the initial selection_id
    selection_id()

    cleanup_old_selections()

def cleanup_old_selections():
    # Loop all selection files and compare the last modification time with
    # the current time and delete the selection file when it is older than
    # the livetime.
    path = config.user.confdir + '/rowselection'
    try:
        for f in os.listdir(path):
            if f[1] != '.' and f.endswith('.mk'):
                p = path + '/' + f
                if time.time() - os.stat(p).st_mtime > config.selection_livetime:
                    os.unlink(p)
    except OSError:
        pass # no directory -> no cleanup

# Generates a selection id or uses the given one
def selection_id():
    if not html.has_var('selection'):
        sel_id = lib.gen_id()
        html.set_var('selection', sel_id)
        return sel_id
    else:
        sel_id = html.var('selection')
        # Avoid illegal file access by introducing .. or /
        if not re.match("^[-0-9a-zA-Z]+$", sel_id):
            new_id = lib.gen_id()
            html.set_var('selection', new_id)
            return new_id
        else:
            return sel_id

def get_rowselection(ident):
    vo = config.user.load_file("rowselection/%s" % selection_id(), {})
    return vo.get(ident, [])

def set_rowselection(ident, rows, action):
    vo = config.user.load_file("rowselection/%s" % selection_id(), {}, lock=True)

    if action == 'set':
        vo[ident] = rows

    elif action == 'add':
        vo[ident] = list(set(vo.get(ident, [])).union(rows))

    elif action == 'del':
        vo[ident] = list(set(vo.get(ident, [])) - set(rows))

    elif action == 'unset':
        del vo[ident]

    config.user.save_file("rowselection/%s" % selection_id(), vo, unlock=True)

def ajax_set_rowselection():
    ident = html.var('id')

    action = html.var('action', 'set')
    if action not in [ 'add', 'del', 'set', 'unset' ]:
        raise lib.MKUserError(None, _('Invalid action'))

    rows  = html.var('rows', '').split(',')

    set_rowselection(ident, rows, action)


#.
#   .--Display Opts.-------------------------------------------------------.
#   |       ____  _           _                ___        _                |
#   |      |  _ \(_)___ _ __ | | __ _ _   _   / _ \ _ __ | |_ ___          |
#   |      | | | | / __| '_ \| |/ _` | | | | | | | | '_ \| __/ __|         |
#   |      | |_| | \__ \ |_) | | (_| | |_| | | |_| | |_) | |_\__ \_        |
#   |      |____/|_|___/ .__/|_|\__,_|\__, |  \___/| .__/ \__|___(_)       |
#   |                  |_|            |___/        |_|                     |
#   +----------------------------------------------------------------------+
#   | Display options are flags that control which elements of a view      |
#   | should be displayed (buttons, sorting, etc.). They can be  specified |
#   | via the URL variable display_options.                                |
#   | An upper-case char means enabled, lower-case means disabled.         |
#   '----------------------------------------------------------------------'

display_options = None

class DisplayOptions(object):
    H = "H" # The HTML header and body-tag (containing the tags <HTML> and <BODY>)
    T = "T" # The title line showing the header and the logged in user
    B = "B" # The blue context buttons that link to other views
    F = "F" # The button for using filters
    C = "C" # The button for using commands and all icons for commands (e.g. the reschedule icon)
    O = "O" # The view options number of columns and refresh
    D = "D" # The Display button, which contains column specific formatting settings
    E = "E" # The button for editing the view
    Z = "Z" # The footer line, where refresh: 30s is being displayed
    R = "R" # The auto-refreshing in general (browser reload)
    S = "S" # The playing of alarm sounds (on critical and warning services)
    U = "U" # Load persisted user row selections
    I = "I" # All hyperlinks pointing to other views
    X = "X" # All other hyperlinks (pointing to external applications like PNP, WATO or others)
    M = "M" # If this option is not set, then all hyperlinks are targeted to the HTML frame
            # with the name main. This is useful when using views as elements in the dashboard.
    L = "L" # The column title links in multisite views
    W = "W" # The limit and livestatus error message in views
    N = "N" # Switching to inline display mode when disabled
            # (e.g. no padding round page)


    @classmethod
    def all_on(cls):
        opts = ""
        for k in sorted(cls.__dict__.keys()):
            if len(k) == 1:
                opts += k
        return opts


    @classmethod
    def all_off(cls):
        return cls.all_on().lower()


    def __init__(self):
        self.options       = self.all_off()
        self.title_options = None


    def load_from_html(self):
        # Parse display options and
        if html.output_format == "html":
            options = html.var("display_options", "")
        else:
            options = display_options.all_off()

        # Remember the display options in the object for later linking etc.
        self.options = self._merge_with_defaults(options)

        # This is needed for letting only the data table reload. The problem is that
        # the data table is re-fetched via javascript call using special display_options
        # but these special display_options must not be used in links etc. So we use
        # a special var _display_options for defining the display_options for rendering
        # the data table to be reloaded. The contents of "display_options" are used for
        # linking to other views.
        if html.has_var('_display_options'):
            self.options = self._merge_with_defaults(html.var("_display_options", ""))

        # But there is one special case: The sorter links! These links need to know
        # about the provided display_option parameter. The links could use
        # "display_options.options" but this contains the implicit options which should
        # not be added to the URLs. So the real parameters need to be preserved for
        # this case.
        self.title_options = html.var("display_options")

        # If display option 'M' is set, then all links are targetet to the 'main'
        # frame. Also the display options are removed since the view in the main
        # frame should be displayed in standard mode.
        if self.disabled(self.M):
            html.set_link_target("main")
            html.del_var("display_options")


    # If all display_options are upper case assume all not given values default
    # to lower-case. Vice versa when all display_options are lower case.
    # When the display_options are mixed case assume all unset options to be enabled
    def _merge_with_defaults(self, opts):
        do_defaults = self.all_off() if opts.isupper() else self.all_on()
        for c in do_defaults:
            if c.lower() not in opts.lower():
                opts += c
        return opts


    def enabled(self, opt):
        return opt in self.options


    def disabled(self, opt):
        return opt not in self.options



def prepare_display_options(context):
    global display_options

    display_options = DisplayOptions()
    display_options.load_from_html()

    context["display_options"] = display_options
