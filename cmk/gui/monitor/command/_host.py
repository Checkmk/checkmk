#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What every page that offers a host may do with it, in one place."""

from dataclasses import dataclass

from cmk.gui.config import Config
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser

HOST_SUPPORTED_ACTIONS: tuple[str, ...] = (
    "acknowledge",
    "schedule_downtimes",
    "reschedule",
    "remove_acknowledgments",
    "remove_downtimes_hosts_services",
    "send_custom_notification",
    "add_comment",
    "fake_check_result",
)


@dataclass(frozen=True, kw_only=True)
class HostSetupLink:
    """A link into Setup, its url carrying the host as the `{host}` placeholder."""

    ident: str
    title: str
    icon: str
    url: str


def host_setup_links(config: Config, user: LoggedInUser) -> list[HostSetupLink]:
    if not config.wato_enabled:
        return []
    links: list[HostSetupLink] = []
    if user.may("wato.use") and (user.may("wato.seeall") or user.may("wato.hosts")):
        links.append(
            HostSetupLink(
                ident="edit",
                title=_("Edit host"),
                icon="edit",
                url="wato.py?mode=edit_host&host={host}",
            )
        )
    if user.may("wato.rulesets"):
        links.append(
            HostSetupLink(
                ident="parameters",
                title=_("Parameters"),
                icon="rulesets",
                url="wato.py?mode=object_parameters&host={host}",
            )
        )
    return links
