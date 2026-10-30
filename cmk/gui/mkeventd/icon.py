#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

import re
import shlex
import string
from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.ccc.site import SiteId
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.sites import get_alias_of_host, SiteStatus, states
from cmk.gui.type_defs import Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.icon import Icon, IconConfig
from cmk.ruleset_matcher.tags import TagID
from cmk.web.utils.icons import DynamicIcon, DynamicIconName, StaticIcon
from cmk.web.utils.urls import makeuri_contextless


def _render_mkeventd_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],  # noqa: ARG001
    custom_vars: Mapping[str, str],  # noqa: ARG001
    user_permissions: UserPermissions,  # noqa: ARG001
    icon_config: IconConfig,
) -> None | tuple[StaticIcon | DynamicIcon, str, str]:
    if not icon_config.mkeventd_enabled:
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

    app = None

    # Extract parameters from check_command
    args = shlex.split(splitted_command[1])
    if not args:
        return None

    if "--" in args:
        # The host and the application follow the end of the options.
        quoted = "-q" in args[: args.index("--")]
        args = args[args.index("--") + 1 :]
    else:
        quoted = "-q" in args
        # First, we remove options without arguments
        for element in ["-a", "-L", "-l", "-q"]:
            if element in args:
                args.remove(element)

        # Then, we remove options with 1 argument
        for i, element in enumerate(args):
            if element in ["-H", "-s"]:
                args = args[:i] + args[i + 2 :]

    hosts = _split_host_spec(args[0], row["site"], quoted) if args else []
    host = _get_hostname(hosts, row)

    # If we have no host then the command line from the check_command seems
    # to be garbled. Better show nothing in this case.
    if not host:
        return None

    monitored = _is_monitored_host_spec(hosts, row)
    link_host = row["host_name"] if monitored else host
    url_vars = [
        ("view_name", "ec_events_of_monhost" if monitored else "ec_events_of_host"),
        ("site", row["site"]),
        ("host", link_host),
        *([] if monitored else [("event_host", host)]),
    ]

    title = _("Events of host %(host_name)s") % {"host_name": link_host}

    if len(args) >= 2:
        app = _unescape(args[1], row["site"])
        title = _('Events of application "%(app)s" on host %(host)s') % {
            "app": app,
            "host": link_host,
        }
        url_vars.append(("event_application", app))

    return (
        DynamicIconName("mkeventd"),  # TODO: this should be a static icon!
        title,
        makeuri_contextless(request, url_vars, filename="view.py"),
    )


MkeventdIcon = Icon(
    ident="mkeventd",
    title=_l("Events"),
    toplevel=False,
    sort_index=30,
    columns=["check_command"],
    host_columns=["address", "alias", "name"],
    render=_render_mkeventd_icon,
)


def _is_monitored_host_spec(hosts: Sequence[str], row: Row) -> bool:
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
    return {host.lower() for host in hosts} <= {name.lower() for name in own}


def _get_hostname(hosts: Sequence[str], row: Row) -> str:
    first = hosts[0] if hosts else ""
    if first == "$HOSTNAME$":
        return row["host_name"]
    if first == "$HOSTADDRESS$":
        return row["host_address"]
    if first == "$HOSTALIAS$":
        return get_alias_of_host(row["site"], row["host_name"])
    return "/".join(hosts)


def _split_host_spec(arg: str, site_id: SiteId, quoted: bool) -> list[str]:
    """Split the host specification at the slashes like check_mkevents does

    With -q, a backslash quotes a following slash or backslash. Like for the check,
    whitespace around a host doesn't count, and empty hosts are dropped."""
    spec = _unescape(arg, site_id)
    if quoted:
        hosts = [""]
        for token in re.findall(r"\\[/\\]|.", spec, re.DOTALL):
            if token == "/":
                hosts.append("")
            else:
                hosts[-1] += token[-1]
    else:
        hosts = spec.split("/")
    # Like the check and the EC, we strip only ASCII whitespace, not the Unicode one.
    return [stripped for host in hosts if (stripped := host.strip(string.whitespace))]


def _unescape(arg: str, site_id: SiteId) -> str:
    """Undo the escaping of the check command in the core config

    Both cores put a backslash in front of "!", but only Nagios doubles backslashes."""
    if "\\\\" in arg and states().get(site_id, SiteStatus()).get("core") == "nagios":
        arg = arg.replace("\\\\", "\\")
    return arg.replace("\\!", "!")
