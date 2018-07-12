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

import cmk.gui.watolib as watolib
from cmk.gui.i18n import _

def global_buttons():
    changelog_button()
    home_button()


def home_button():
    html.context_button(_("Main Menu"), watolib.folder_preserving_link([("mode", "main")]), "home")


def changelog_button():
    num_pending = watolib.get_number_of_pending_changes()
    if num_pending >= 1:
        hot = True
        icon = "wato_changes"

        if num_pending == 1:
            buttontext = _("1 change")
        else:
            buttontext = _("%d changes") % num_pending

    else:
        buttontext = _("No changes")
        hot = False
        icon = "wato_nochanges"
    html.context_button(buttontext, watolib.folder_preserving_link([("mode", "changelog")]), icon, hot)


def host_status_button(hostname, viewname):
    html.context_button(_("Status"),
       "view.py?" + html.urlencode_vars([
           ("view_name", viewname),
           ("filename", watolib.Folder.current().path() + "/hosts.mk"),
           ("host",     hostname),
           ("site",     "")]),
           "status")


def service_status_button(hostname, servicedesc):
    html.context_button(_("Status"),
       "view.py?" + html.urlencode_vars([
           ("view_name", "service"),
           ("host",     hostname),
           ("service",  servicedesc),
           ]),
           "status")


def folder_status_button(viewname = "allhosts"):
    html.context_button(_("Status"),
       "view.py?" + html.urlencode_vars([
           ("view_name", viewname),
           ("wato_folder", watolib.Folder.current().path())]),
           "status")
