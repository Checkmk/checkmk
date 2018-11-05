#!/usr/bin/env python
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
"""Bulk inventory and other longer procedures are separated in single
steps and run by an JavaScript scheduler showing a progress bar and
buttons for aborting and pausing."""

import json

import cmk.gui.watolib as watolib
from cmk.gui.globals import html
from cmk.gui.i18n import _


# success_stats: Fields from the stats list to use for checking if something has been found
# fail_stats:    Fields from the stats list to used to count failed elements
def interactive_progress(items,
                         title,
                         stats,
                         finishvars,
                         timewait,
                         success_stats=None,
                         termvars=None,
                         fail_stats=None):
    if success_stats is None:
        success_stats = []

    if termvars is None:
        termvars = []

    if fail_stats is None:
        fail_stats = []

    if not termvars:
        termvars = finishvars

    html.open_center()
    html.open_table(class_="progress")

    html.open_tr()
    html.th(title, colspan=2)
    html.close_tr()

    html.open_tr()
    html.td(html.render_div('', id_="progress_log"), colspan=2, class_="log")
    html.close_tr()

    html.open_tr()
    html.open_td(colspan=2, class_="bar")
    html.open_table(id_="progress_bar")
    html.open_tbody()
    html.open_tr()
    html.td('', class_="left")
    html.td('', class_="right")
    html.close_tr()
    html.close_tbody()
    html.close_table()
    html.div('', id_="progress_title")
    html.img("images/perfometer-bg.png", class_="glass")
    html.close_td()
    html.close_tr()

    html.open_tr()
    html.open_td(class_="stats")
    html.open_table()
    for num, (label, value) in enumerate(stats):
        html.open_tr()
        html.th(label)
        html.td(value, id_="progress_stat%d" % num)
        html.close_tr()
    html.close_table()
    html.close_td()

    html.open_td(class_="buttons")
    html.jsbutton('progress_pause',    _('Pause'),   'javascript:progress_pause()')
    html.jsbutton('progress_proceed',  _('Proceed'), 'javascript:progress_proceed()',  'display:none')
    html.jsbutton('progress_finished', _('Finish'),  'javascript:progress_end()', 'display:none')
    html.jsbutton('progress_retry',    _('Retry Failed Hosts'), 'javascript:progress_retry()', 'display:none')
    html.jsbutton('progress_restart',  _('Restart'), 'javascript:location.reload()')
    html.jsbutton('progress_abort',    _('Abort'),   'javascript:progress_end()')
    html.close_td()
    html.close_tr()

    html.close_table()
    html.close_center()

    # Remove all sel_* variables. We do not need them for our ajax-calls.
    # They are just needed for the Abort/Finish links. Those must be converted
    # to POST.
    base_url = html.makeuri([], remove_prefix="sel")
    finish_url = watolib.folder_preserving_link([("mode", "folder")] + finishvars)
    term_url = watolib.folder_preserving_link([("mode", "folder")] + termvars)

    html.javascript(('progress_scheduler("%s", "%s", 50, %s, "%s", %s, %s, "%s", "' + _("FINISHED.") + '");') %
                     (html.var('mode'), base_url, json.dumps(items), finish_url,
                      json.dumps(success_stats), json.dumps(fail_stats), term_url))
