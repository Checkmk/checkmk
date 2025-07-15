#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import shlex
from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.sites import get_alias_of_host
from cmk.gui.type_defs import Row
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.views.icon import Icon
from cmk.utils.tags import TagID


def _render_mkeventd_icon(
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
        host = _get_hostname(args, row)

    # If we have no host then the command line from the check_command seems
    # to be garbled. Better show nothing in this case.
    if not host:
        return None

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

    return "mkeventd", title, makeuri_contextless(request, url_vars, filename="view.py")


MkeventdIcon = Icon(
    ident="mkeventd",
    title=_l("Events"),
    toplevel=False,
    sort_index=30,
    columns=["check_command"],
    host_columns=["address", "name"],
    render=_render_mkeventd_icon,
)


def _get_hostname(args: Sequence[str], row: Row) -> str:
    args_splitted = args[0].split("/")
    if args_splitted[0] == "$HOSTNAME$":
        return row["host_name"]
    if args_splitted[0] == "$HOSTADDRESS$":
        return row["host_address"]
    if args_splitted[0] == "$HOSTALIAS$":
        return get_alias_of_host(row["site"], row["host_name"])
    return args[0]
