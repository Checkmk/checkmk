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

from ast import literal_eval
import config
import defaults
import lib

g_acknowledgement_path = defaults.var_dir + "/acknowledged_notifications.mk"
g_acknowledgement_time = None

def acknowledge_failed_notifications(timestamp):
    config.need_permission("general.acknowledge_failed_notifications")
    global g_acknowledgement_time
    g_acknowledgement_time = timestamp
    save_acknowledgements()

def save_acknowledgements():
    config.need_permission("general.acknowledge_failed_notifications")
    with open(g_acknowledgement_path, "w") as f:
        f.write("%r\n" % g_acknowledgement_time)

def acknowledged_time():
    if g_acknowledgement_time is None:
        load_acknowledgements()
    return g_acknowledgement_time

def load_acknowledgements():
    global g_acknowledgement_time
    with open(g_acknowledgement_path, "r") as f:
        content = f.read().strip()
        if content:
            g_acknowledgement_time = literal_eval(content)

    return []

def render_page_confirm(acktime, prev_url):
    html.set_render_headfoot(False)
    html.header(_("Confirm"), javascripts=[], stylesheets=[ "pages", "check_mk" ])
    html.debug_vars()
    html.write('<div class="really">\n')
    html.write(_("Do you really want to acknowledge all failed notifications up to %s?</br>"
                 "This removes the warning for all users.") % lib.datetime_human_readable(acktime))
    html.begin_form("confirm", method="GET", action=prev_url)
    html.hidden_field('acktime', acktime),
    html.image_button('_confirm', _("Yes"))
    html.end_form()
    html.write('</div>\n')

    html.footer()

def render_page_done():
    html.set_render_headfoot(False)
    html.header(_("Confirm"), javascripts=[], stylesheets=[ "pages", "check_mk" ])
    html.write('<div class="really">\n')
    html.write('Done')
    html.write('</div>')
    html.jsbutton('_back', _("Back"), "window.history.go(-2); window.location.reload();")
    html.footer()

def page_clear():
    acktime = float(html.var('acktime'))
    prev_url = html.var('prev_url')
    if html.var('_confirm'):
        acknowledge_failed_notifications(acktime)
        render_page_done()
    else:
        render_page_confirm(acktime, prev_url)

