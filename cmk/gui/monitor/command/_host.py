#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What every page that offers a host may do with it."""

from dataclasses import dataclass
from typing import Protocol

from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser
from cmk.shared_typing.monitoring.action_ident import HostActionIdent

# The shared types declare the host commands, so the frontend can tell it implements them all.
HOST_SUPPORTED_ACTIONS: tuple[HostActionIdent, ...] = tuple(HostActionIdent)


@dataclass(frozen=True, kw_only=True)
class HostSetupLink:
    """A link into Setup, its url carrying the host as the `{host}` placeholder."""

    ident: str
    title: str
    icon: str
    url: str


class SetupSwitch(Protocol):
    """The part of a configuration that says whether Setup is there to link to."""

    @property
    def wato_enabled(self) -> bool: ...


def host_setup_links(config: SetupSwitch, user: LoggedInUser) -> list[HostSetupLink]:
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
