#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import shlex

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.plugins.views.icons.utils import Icon, icon_and_action_registry
from cmk.gui.site_config import get_site_config
from cmk.gui.sites import get_alias_of_host
from cmk.gui.utils.urls import urlencode_vars


@icon_and_action_registry.register
class MkeventdIcon(Icon):
    @classmethod
    def ident(cls):
        return "mkeventd"

    @classmethod
    def title(cls) -> str:
        return _("Events")

    def default_toplevel(self):
        return False

    def default_sort_index(self):
        return 30

    def columns(self):
        return ["check_command"]

    def host_columns(self):
        return ["address", "name"]

    def render(self, what, row, tags, custom_vars):
        if not active_config.mkeventd_enabled:
            return None

        # show for services based on the mkevents active check
        command = row[what + "_check_command"]

        if what != "service" or not command.startswith("check_mk_active-mkevents"):
            return None

        # Split command by the parts (COMMAND!ARG0!...) Beware: Do not split by escaped exclamation mark.
        splitted_command = re.split(r"(?<!\\)!", command)

        # All arguments are space separated in in ARG0
        if len(splitted_command) != 2:
            return None

        host = None
        app = None

        # Extract parameters from check_command
        args = shlex.split(splitted_command[1])
        if not args:
            return None

        # Handle -a and -H options. Sorry for the hack. We currently
        # have no better idea
        if len(args) >= 2 and args[0] == "-H":
            args = args[2:]  # skip two arguments
        if len(args) >= 1 and args[0] == "-a":
            args = args[1:]

        if len(args) >= 1:
            host = _get_hostname(args, row)

        # If we have no host then the command line from the check_command seems
        # to be garbled. Better show nothing in this case.
        if not host:
            return None

        # It is possible to have a central event console, this is the default case.
        # Another possible architecture is to have an event console in each site in
        # a distributed environment. For the later case the base url need to be
        # constructed here
        url_prefix = ""
        if getattr(active_config, "mkeventd_distributed", False):
            site = get_site_config(row["site"])
            url_prefix = site["url_prefix"] + "check_mk/"

        url_vars = [
            ("view_name", "ec_events_of_monhost"),
            ("site", row["site"]),
            ("host", row["host_name"]),
        ]

        title = _("Events of Host %s") % (row["host_name"])

        if len(args) >= 2:
            app = args[1].strip("'").replace("\\\\", "\\").replace("\\!", "!")
            title = _('Events of Application "%s" on Host %s') % (app, host)
            url_vars.append(("event_application", app))

        url = "view.py?" + urlencode_vars(url_vars)

        return "mkeventd", title, url_prefix + url


def _get_hostname(args, row) -> str:
    args_splitted = args[0].split("/")
    if args_splitted[0] == "$HOSTNAME$":
        return row["host_name"]
    if args_splitted[0] == "$HOSTADDRESS$":
        return row["host_address"]
    if args_splitted[0] == "$HOSTALIAS$":
        return get_alias_of_host(row["site"], row["host_name"])
    return args[0]
