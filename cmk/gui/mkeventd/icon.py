#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import shlex
from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.utils.tags import TagID

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.site_config import get_site_config
from cmk.gui.type_defs import ColumnName, Row
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.views.icon import Icon


class MkeventdIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "mkeventd"

    @classmethod
    def title(cls) -> str:
        return _("Events")

    def default_toplevel(self) -> bool:
        return False

    def default_sort_index(self) -> int:
        return 30

    def columns(self) -> Sequence[ColumnName]:
        return ["check_command"]

    def host_columns(self) -> list[str]:
        return ["address", "alias", "name"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | tuple[str, str, str]:
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

        # First, we remove options without arguments
        for element in ["-a", "-L", "-l"]:
            if element in args:
                args.remove(element)

        # Then, we remove options with 1 argument
        for i, element in enumerate(args):
            if element in ["-H", "-s"]:
                args = args[:i] + args[i + 2 :]

        if len(args) >= 1:
            host = args[0]

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
            site = get_site_config(active_config, row["site"])
            url_prefix = site["url_prefix"] + "check_mk/"

        monitored = _is_monitored_host_spec(args[0], row)
        link_host = row["host_name"] if monitored else host
        url_vars = [
            ("view_name", "ec_events_of_monhost" if monitored else "ec_events_of_host"),
            ("site", row["site"]),
            ("host", link_host),
            *([] if monitored else [("event_host", host)]),
        ]

        title = _("Events of Host %s") % link_host

        if len(args) >= 2:
            app = args[1].strip("'").replace("\\\\", "\\").replace("\\!", "!")
            title = _('Events of Application "%s" on Host %s') % (app, link_host)
            url_vars.append(("event_application", app))

        url = "view.py?" + urlencode_vars(url_vars)

        return "mkeventd", title, url_prefix + url


def _is_monitored_host_spec(hostspec: str, row: Row) -> bool:
    """Macros in the host spec are resolved when the command line is built, so
    compare with the monitored host's name, address and alias - case-insensitively,
    like the event_host filter of the EC"""
    own = {
        "$HOSTNAME$",
        "$HOSTADDRESS$",
        "$HOSTALIAS$",
        row["host_name"],
        row["host_address"],
        row["host_alias"],
    }
    return {part.lower() for part in hostspec.split("/")} <= {name.lower() for name in own}
