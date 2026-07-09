#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mint signed Maps tickets for the logged-in Checkmk user.

The Maps backend daemon performs no user/session handling of its own. The GUI —
which has the full RBAC / 2FA context — mints a short-lived ticket carrying the
user's pre-resolved capabilities, signed with the site-internal secret. The
daemon validates it with the same secret (see ``cmk.maps.backend.core.auth``).
The byte-for-byte token format lives in :mod:`cmk.maps.shared.ticket`, which both
this minting side and the daemon's validator import — this module only resolves
RBAC into capabilities and hands them to the shared encoder.
"""

import time
from collections.abc import Mapping

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.user_sites import get_configured_site_choices
from cmk.gui.watolib.groups_io import load_group_information
from cmk.maps.shared.ticket import (
    Choice,
    encode_ticket,
    MapClaim,
    sign_config,
    STREAM_TICKET_AUDIENCE,
    StreamCapabilities,
    StreamTicketClaims,
    TicketCapabilities,
    TicketClaims,
)
from cmk.utils.local_secrets import SiteInternalSecret

# Default ticket lifetime; the SPA refreshes before expiry.
TICKET_TTL_SECONDS = 300

# The SSE stream token shares the API ticket's lifetime on purpose: the SPA
# re-mints both on one timer (well inside the TTL), so a shorter stream TTL would
# expire the token between refreshes and break a long-open stream. The stream
# token's protection comes from its reduced capabilities and its own audience
# (it is useless on the REST API and carries no command/publish/edit grant), not
# from a shorter window.
STREAM_TICKET_TTL_SECONDS = TICKET_TTL_SECONDS

# Host/service command verb -> the Checkmk permission that authorises it. Single
# source of truth: drives the GUI command RBAC (cmk.maps.gui._commands._ACTIONS)
# and the verb set baked into the ticket's ``commands`` capability (see below).
COMMAND_ACTION_PERMISSIONS: dict[str, str] = {
    "acknowledge": "action.acknowledge",
    "remove_acknowledgement": "action.acknowledge",
    "force_check": "action.reschedule",
    "schedule_downtime": "action.downtimes",
    "add_comment": "action.addcomment",
    "enable_notifications": "action.notifications",
    "disable_notifications": "action.notifications",
    "enable_checks": "action.enablechecks",
    "disable_checks": "action.enablechecks",
}


def _publishable_contact_groups(user: LoggedInUser) -> list[Choice]:
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


def _publishable_sites(user: LoggedInUser) -> list[Choice]:
    """Sites (id + alias) the user may share a map with — the configured sites
    they're authorized for. Empty when they can't publish to sites.
    """
    if not user.may("general.publish_to_sites_map"):
        return []
    return [Choice(id=str(sid), alias=alias) for sid, alias in get_configured_site_choices()]


def gather_capabilities(user: LoggedInUser) -> TicketCapabilities:
    """Resolve the user's Maps capabilities once, for baking into a ticket."""
    return TicketCapabilities(
        # ``general.edit_map`` (the pagetype create/edit grant) — the daemon gates
        # its own write endpoints with it; per-map view/edit is enforced GUI-side.
        may_edit=user.may("general.edit_map"),
        configure=user.may("maps.configure"),
        # Livestatus contact-group bypass (admins / general.see_all).
        see_all=user.may("general.see_all"),
        # Independent SETUP-folder read scope.
        folder_see_all=user.may("wato.see_all_folders"),
        contact_groups=sorted(str(cg) for cg in user.contact_groups),
        # Visibility/publish scopes the Access editor may offer, mirroring the
        # pagetype visibility form (general.publish_*_map). The server still
        # re-clamps the chosen value on save (the Maps REST create/update
        # endpoints), so these only drive which options the UI shows.
        publish_all=user.may("general.publish_map"),
        publish_to_groups=user.may("general.publish_to_groups_map"),
        publish_to_foreign_groups=user.may("general.publish_to_foreign_groups_map"),
        publish_to_sites=user.may("general.publish_to_sites_map"),
        # Contact groups the Access editor can offer when sharing to specific
        # groups — the full set for users who may publish to foreign groups,
        # otherwise just their own. Empty when the user can't publish to groups.
        all_contact_groups=_publishable_contact_groups(user),
        # Sites the Access editor can offer when sharing to specific sites.
        all_sites=_publishable_sites(user),
        commands=sorted(
            verb for verb, perm in COMMAND_ACTION_PERMISSIONS.items() if user.may(perm)
        ),
    )


def gather_stream_capabilities(user: LoggedInUser) -> StreamCapabilities:
    """The minimal cap set the SSE stream token needs — read/scope only.

    The daemon's SSE path consumes only the Livestatus contact scope (``see_all``
    + ``contact_groups``) and the SETUP-folder read scope (``folder_see_all``);
    it never touches commands, publish scopes, ``may_edit`` or ``configure``.
    Baking ONLY these into the URL-borne token means a token captured from an
    access log grants no more than the read access the user already had to the
    one map it is bound to — no privilege to escalate.
    """
    return StreamCapabilities(
        see_all=user.may("general.see_all"),
        folder_see_all=user.may("wato.see_all_folders"),
        contact_groups=sorted(str(cg) for cg in user.contact_groups),
    )


def mint_stream_ticket(
    user: LoggedInUser,
    *,
    map_claim: MapClaim,
    now: float | None = None,
) -> str:
    """Return the reduced-capability, map-bound SSE stream token.

    Signed with the same site-internal secret as the API ticket but under the
    stream audience (:data:`cmk.maps.shared.ticket.STREAM_TICKET_AUDIENCE`),
    so the daemon accepts it only on the SSE endpoint and rejects it everywhere
    else. Always map-scoped (the SSE stream is per-map): the map's real
    ``{"owner", "name"}`` is baked in so the daemon keys its shared broadcast loop
    by the true owner without trusting a client value.
    """
    expiry = int(time.time() if now is None else now) + STREAM_TICKET_TTL_SECONDS
    claims: StreamTicketClaims = {
        "sub": str(user.ident),
        "exp": expiry,
        "caps": gather_stream_capabilities(user),
        "map": map_claim,
    }
    return encode_ticket(claims, SiteInternalSecret().secret.hmac, audience=STREAM_TICKET_AUDIENCE)


def sign_map_config(config: Mapping[str, object], *, owner: str) -> dict[str, str]:
    """Sign a resolved map config so the daemon can trust it.

    The GUI resolved ``config`` from the pagetype store (``get_permitted_map``),
    so it is canonical and permission-checked. It serialises the config once and
    signs the exact bytes (with the map ``owner`` folded in) with the site-internal
    secret. The SPA relays the returned ``{config_b64, sig}`` VERBATIM to the
    daemon (it parses ``config_b64`` for its own render but never re-serialises
    what it forwards), and the daemon verifies the same bytes against the ticket's
    owner before trusting the config for its broadcast loop — so a viewer can't
    substitute a tampered config, nor relay one signed for a foreign owner, and
    there is no dict-vs-model normalisation drift. The signing wire format is owned
    by :func:`cmk.maps.shared.ticket.sign_config`, which the daemon's
    verifier shares.
    """
    return sign_config(config, SiteInternalSecret().secret.hmac, owner=owner)


def mint_ticket(
    user: LoggedInUser,
    *,
    caps: TicketCapabilities | None = None,
    map_claim: MapClaim | None = None,
    now: float | None = None,
) -> str:
    """Return a signed ticket for *user* valid for :data:`TICKET_TTL_SECONDS`.

    Pass ``caps`` to reuse an already-gathered capability set (the ticket
    endpoint returns the same set to the SPA) and avoid resolving it twice.

    Pass ``map_claim`` to bind the ticket to a specific map. The GUI resolves the
    map the user is authorised to open (``get_permitted_map``) and bakes the map's
    real ``{"owner", "name"}`` in — so the daemon can key its shared broadcast
    loop by the map's true owner (not the viewer) without trusting a client value.
    Omitted for the map-list / global phase before a map is opened.
    """
    expiry = int(time.time() if now is None else now) + TICKET_TTL_SECONDS
    claims: TicketClaims = {
        "sub": str(user.ident),
        "exp": expiry,
        "caps": gather_capabilities(user) if caps is None else caps,
    }
    if map_claim is not None:
        claims["map"] = map_claim
    return encode_ticket(claims, SiteInternalSecret().secret.hmac)
