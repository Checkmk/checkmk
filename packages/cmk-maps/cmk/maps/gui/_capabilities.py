#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What the logged-in user may do in Maps, resolved for the SPA.

The daemon resolves the user and the permissions it needs itself, from the GUI
session (``gui_session/identify``). What is resolved here only decides what the
SPA offers. The map config the SPA relays to the daemon is signed here too.
"""

from collections.abc import Mapping
from typing import Literal, TypedDict

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.user_sites import get_configured_site_choices
from cmk.gui.watolib.groups_io import load_group_information
from cmk.maps.shared.map_signature import sign_config
from cmk.utils.local_secrets import SiteInternalSecret

# The monitoring commands the SPA offers. The REST model puts the alternatives
# into the generated OpenAPI, so the SPA shows a button only for a verb it knows.
type CommandVerb = Literal[
    "acknowledge",
    "remove_acknowledgement",
    "force_check",
    "schedule_downtime",
    "remove_all_downtimes",
    "add_comment",
    "enable_notifications",
    "disable_notifications",
    "enable_checks",
    "disable_checks",
]

# Host/service command verb -> the Checkmk permission that authorises it, on top
# of ``general.act``. Single source of truth: drives the GUI command RBAC
# (cmk.maps.gui._commands), the verbs the SPA offers (see below) and the
# permissions the command endpoint declares.
COMMAND_ACTION_PERMISSIONS: dict[CommandVerb, str] = {
    "acknowledge": "action.acknowledge",
    "remove_acknowledgement": "action.acknowledge",
    "force_check": "action.reschedule",
    "schedule_downtime": "action.downtimes",
    # The views offer lifting every downtime of an object only with this one.
    "remove_all_downtimes": "action.remove_all_downtimes",
    "add_comment": "action.addcomment",
    "enable_notifications": "action.notifications",
    "disable_notifications": "action.notifications",
    "enable_checks": "action.enablechecks",
    "disable_checks": "action.enablechecks",
}


class Choice(TypedDict):
    """An (id, alias) pair the SPA's Access editor offers — a contact group or a site."""

    id: str
    alias: str


class Capabilities(TypedDict):
    may_edit: bool
    configure: bool
    publish_all: bool
    publish_to_groups: bool
    publish_to_foreign_groups: bool
    publish_to_sites: bool
    all_contact_groups: list[Choice]
    all_sites: list[Choice]
    commands: list[CommandVerb]


def publishable_contact_groups(user: LoggedInUser) -> list[Choice]:
    """Contact groups (id + alias) the user may share a map with.

    The full configured set when the user may publish to foreign groups, else
    only their own groups. Empty when they can't publish to groups at all —
    mirrors the choices the visuals visibility form offers.
    """
    if not user.may("general.publish_to_groups_map"):
        return []
    groups = load_group_information()["contact"]
    if user.may("general.publish_to_foreign_groups_map"):
        allowed = set(groups)
    else:
        allowed = {str(cg) for cg in user.contact_groups}
    return [
        Choice(id=gid, alias=str(groups[gid].get("alias") or gid))
        for gid in sorted(allowed)
        if gid in groups
    ]


def publishable_sites(user: LoggedInUser) -> list[Choice]:
    """Sites (id + alias) the user may share a map with — the configured sites
    they're authorized for. Empty when they can't publish to sites.
    """
    if not user.may("general.publish_to_sites_map"):
        return []
    return [Choice(id=str(sid), alias=alias) for sid, alias in get_configured_site_choices()]


def _granted_commands(user: LoggedInUser) -> list[CommandVerb]:
    """The verbs the user may send; none without the views' command gate."""
    if not user.may("general.act"):
        return []
    return sorted(verb for verb, perm in COMMAND_ACTION_PERMISSIONS.items() if user.may(perm))


def gather_capabilities(user: LoggedInUser) -> Capabilities:
    return Capabilities(
        may_edit=user.may("general.edit_map"),
        configure=user.may("maps.configure"),
        # Visibility/publish scopes the Access editor may offer, mirroring the
        # pagetype visibility form (general.publish_*_map). The server still
        # re-clamps the chosen value on save (the Maps REST create/update
        # endpoints), so these only drive which options the UI shows.
        publish_all=user.may("general.publish_map"),
        publish_to_groups=user.may("general.publish_to_groups_map"),
        publish_to_foreign_groups=user.may("general.publish_to_foreign_groups_map"),
        publish_to_sites=user.may("general.publish_to_sites_map"),
        all_contact_groups=publishable_contact_groups(user),
        all_sites=publishable_sites(user),
        commands=_granted_commands(user),
    )


def sign_map_config(config: Mapping[str, object], *, owner: str) -> dict[str, str]:
    """Sign a resolved map config so the daemon can trust it.

    The GUI resolved ``config`` from the pagetype store (``get_permitted_map``),
    so it is canonical and permission-checked. The SPA relays the returned
    ``{config_b64, sig}`` verbatim to the daemon (it parses ``config_b64`` for its
    own render but never re-serialises what it forwards), and the daemon verifies
    the same bytes against the owner the GUI names for the map before trusting
    the config for its broadcast loop.
    """
    return sign_config(config, SiteInternalSecret().secret.hmac, owner=owner)
