#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The links into Setup every page offers on a host or a service, in one place.

Which hosts Setup lets the user open is a question per host, left to the pages that show them.
"""

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote_plus

from cmk.gui.i18n import _


@dataclass(frozen=True, kw_only=True)
class SetupLink:
    """A link into Setup, its url carrying the host as the `{host}` placeholder - and, for a link
    on a service, the service as `{service}`."""

    ident: str
    title: str
    icon: str
    url: str

    def url_for(self, *, host: str, service: str | None = None) -> str:
        """The url with the given placeholders filled in, any other left for the reader to fill."""
        url = self.url.replace("{host}", quote_plus(host))
        return url if service is None else url.replace("{service}", quote_plus(service))


class PermissionChecker(Protocol):
    """The part of a user that says which permissions they hold."""

    def may(self, permission_name: str) -> bool: ...


class SetupSwitch(Protocol):
    """The part of a configuration that says whether Setup is there to link to."""

    @property
    def wato_enabled(self) -> bool: ...


def may_reach_setup(config: SetupSwitch, user: PermissionChecker, *permissions: str) -> bool:
    """Whether Setup would serve a page needing the Setup ``permissions``, rather than refuse it.

    Mirrors `ensure_static_permissions`: Setup as a whole has to be reachable, and the page's own
    permissions are waived for those who may see all of it.
    """
    if not config.wato_enabled or not user.may("wato.use"):
        return False
    return user.may("wato.seeall") or all(user.may(f"wato.{p}") for p in permissions)


def host_setup_links(config: SetupSwitch, user: PermissionChecker) -> list[SetupLink]:
    links: list[SetupLink] = []
    if may_reach_setup(config, user, "hosts"):
        links.append(
            SetupLink(
                ident="edit",
                title=_("Edit host"),
                icon="edit",
                url="wato.py?mode=edit_host&host={host}",
            )
        )
    if _may_reach_parameters(config, user):
        links.append(
            SetupLink(
                ident="parameters",
                title=_("Parameters"),
                icon="rulesets",
                url="wato.py?mode=object_parameters&host={host}",
            )
        )
    return links


def service_setup_links(config: SetupSwitch, user: PermissionChecker) -> list[SetupLink]:
    return [link] if (link := service_parameters_link(config, user)) else []


def service_parameters_link(config: SetupSwitch, user: PermissionChecker) -> SetupLink | None:
    if not _may_reach_parameters(config, user):
        return None
    return SetupLink(
        ident="parameters",
        title=_("Parameters"),
        icon="rulesets",
        url="wato.py?mode=object_parameters&host={host}&service={service}",
    )


def _may_reach_parameters(config: SetupSwitch, user: PermissionChecker) -> bool:
    """The pages have offered the parameters to everyone who may edit rules."""
    return config.wato_enabled and user.may("wato.rulesets")
