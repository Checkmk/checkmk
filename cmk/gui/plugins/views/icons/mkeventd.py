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

import re

import cmk.gui.config as config
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.plugins.views.icons import Icon, icon_and_action_registry


@icon_and_action_registry.register
class MkeventdIcon(Icon):
    @classmethod
    def ident(cls):
        return "mkeventd"

    def default_toplevel(self):
        return False

    def default_sort_index(self):
        return 30

    def columns(self):
        return ["check_command"]

    def host_columns(self):
        return ["address", "name"]

    def render(self, what, row, tags, custom_vars):
        if not config.mkeventd_enabled:
            return

        # show for services based on the mkevents active check
        command = row[what + '_check_command']

        if what != 'service' or not command.startswith('check_mk_active-mkevents'):
            return

        # Split command by the parts (COMMAND!ARG0!...) Beware: Do not split by escaped exclamation mark.
        splitted_command = re.split(r'(?<!\\)!', command)

        # All arguments are space separated in in ARG0
        if len(splitted_command) != 2:
            return

        host = None
        app = None

        # Extract parameters from check_command:
        # TODO: Use better argument string splitting (shlex.split())
        args = splitted_command[1].split()
        if not args:
            return

        # Handle -a and -H options. Sorry for the hack. We currently
        # have no better idea
        if len(args) >= 2 and args[0] == '-H':
            args = args[2:]  # skip two arguments
        if len(args) >= 1 and args[0] == '-a':
            args = args[1:]

        if len(args) >= 1:
            if args[0] == '$HOSTNAME$':
                host = row['host_name']
            elif args[0] == '$HOSTADDRESS$':
                host = row['host_address']
            else:
                host = args[0]

        # If we have no host then the command line from the check_command seems
        # to be garbled. Better show nothing in this case.
        if not host:
            return

        # It is possible to have a central event console, this is the default case.
        # Another possible architecture is to have an event console in each site in
        # a distributed environment. For the later case the base url need to be
        # constructed here
        url_prefix = ''
        if getattr(config, 'mkeventd_distributed', False):
            site = config.site(row["site"])
            url_prefix = site['url_prefix'] + 'check_mk/'

        url_vars = [
            ("view_name", "ec_events_of_monhost"),
            ("site", row["site"]),
            ("host", row["host_name"]),
        ]

        title = _('Events of Host %s') % (row["host_name"])

        if len(args) >= 2:
            app = args[1].strip('\'').replace("\\\\", "\\").replace("\\!", "!")
            title = _('Events of Application "%s" on Host %s') % (app, host)
            url_vars.append(("event_application", app))

        url = 'view.py?' + html.urlencode_vars(url_vars)

        return 'mkeventd', title, url_prefix + url
