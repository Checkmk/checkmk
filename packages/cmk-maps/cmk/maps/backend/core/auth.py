#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk-native request authentication for the Maps backend daemon.

The daemon runs behind the site Apache as a reverse proxy and does NOT manage
users, sessions or passwords itself. The Checkmk GUI (``cmk.maps.gui``) — which
has the full session / RBAC / 2FA context — mints a short-lived signed *ticket*
for the logged-in user, and the daemon merely validates it against the shared
site-internal secret. There is no login, JWT or password store in the daemon.

The ticket/map-config wire format lives in :mod:`cmk.maps.shared.ticket`, which
the minting side (``cmk.maps.gui._tickets``) imports too — so the byte-for-byte
token format is owned in one place. This module adds the daemon's concerns on
top: caching the site-internal secret and turning the validated claims into a
:class:`Principal`. The HMAC key is the site-internal secret in
``etc/site_internal.secret``, which the GUI reads through
:class:`~cmk.utils.local_secrets.SiteInternalSecret`.
"""

from __future__ import annotations

import functools
import hmac
from dataclasses import dataclass, field

from cmk.maps.shared.ticket import (
    decode_ticket,
    HmacFn,
    InvalidTicket,
    STREAM_TICKET_AUDIENCE,
    TICKET_AUDIENCE,
    verify_config,
)
from cmk.utils import paths

__all__ = [
    "InvalidTicket",
    "Principal",
    "validate_stream_ticket",
    "validate_ticket",
    "verify_map_config",
]


@dataclass(frozen=True)
class Principal:
    """The authenticated Checkmk user behind a request, as carried by a ticket.

    Capabilities are baked in by the GUI at mint time (it evaluates ``user.may``
    with the full RBAC context); the daemon never re-derives them and keeps no
    permission store of its own.

    Per-map view/edit authorization is deliberately NOT done here. The GUI holds
    the pagetype + RBAC context and is the single authority: it only hands the
    SPA maps the user may see (``get_permitted_map``) and re-checks edit on save
    (``general.edit_map`` in the map REST endpoints). Every Livestatus query the daemon
    runs is additionally bound to the user's contact-group scope (``auth_user``),
    so a map the user registers can never surface monitoring data beyond that
    scope. The daemon therefore carries only what it genuinely needs: the
    Livestatus auth scope, the allowed command verbs, and ``configure`` /
    ``may_edit`` (Checkmk's ``general.edit_map``). The daemon's only mutating
    endpoint is ``POST /register`` (guarded by ticket authentication plus its own
    signed-config / map-ownership checks); ``configure`` / ``may_edit`` today
    only broaden read access to the connection list (``require_connection_read``).
    They are carried in the ticket so a future daemon write endpoint can gate on
    them without a ticket-contract change.
    """

    name: str
    may_edit: bool = False
    configure: bool = False
    # ``see_all`` bypasses Livestatus contact-group filtering (general.see_all / admin).
    see_all: bool = False
    # ``folder_see_all`` is the independent SETUP-folder read scope
    # (wato.see_all_folders); ``contact_groups`` scopes folder reads otherwise.
    folder_see_all: bool = False
    contact_groups: frozenset[str] = field(default_factory=frozenset)
    # The command verbs the GUI pre-authorized for this user at ticket-mint time
    # (``cmk.maps.gui._tickets``). Commands currently execute GUI-side, so no
    # daemon endpoint consumes this yet; it is the forward-looking pre-auth
    # capability for a future daemon command relay (external-connection commands),
    # carried in the ticket so adding that path needs no ticket-contract change.
    commands: frozenset[str] = field(default_factory=frozenset)
    # Map-scoped ticket: the GUI resolved the map the user opened
    # (``get_permitted_map``) and baked its REAL ``(owner, name)`` in, so the
    # daemon keys its shared broadcast loop by the map's true owner (not the
    # viewer) without trusting a client value. ``None`` for the map-list /
    # global phase before a map is opened (falls back to ``name``).
    map_owner: str | None = None
    map_name: str | None = None

    def may_run_command(self, action: str) -> bool:
        return action in self.commands

    @property
    def auth_user(self) -> str | None:
        """Livestatus ``AuthUser`` scope, or ``None`` for see-all access."""
        return None if self.see_all else self.name

    @property
    def map_key_owner(self) -> str:
        """The map owner the daemon keys the shared broadcast loop / map cache
        by: the ticket's map owner when map-scoped (so every viewer of a
        published map shares one loop), else the caller's own namespace.

        A built-in map's owner is the empty string (``UserId.builtin()``), which
        is a real, map-scoped owner — the GUI signs its config under ``""`` and
        keys the shared loop by it. Test ``map_owner is not None`` rather than
        truthiness so that empty owner survives: ``map_owner or self.name`` would
        collapse it to the caller, and the daemon would then verify the config
        signature against the wrong owner and reject every built-in map."""
        return self.map_owner if self.map_owner is not None else self.name


def _principal_from_caps(name: str, caps: dict[str, object], map_claim: object = None) -> Principal:
    def _flag(key: str) -> bool:
        return bool(caps.get(key, False))

    def _names(key: str) -> frozenset[str]:
        raw = caps.get(key, [])
        return frozenset(str(n) for n in raw) if isinstance(raw, list) else frozenset()

    map_owner: str | None = None
    map_name: str | None = None
    if isinstance(map_claim, dict):
        owner = map_claim.get("owner")
        bname = map_claim.get("name")
        if isinstance(owner, str) and isinstance(bname, str):
            map_owner, map_name = owner, bname

    return Principal(
        name=name,
        may_edit=_flag("may_edit"),
        configure=_flag("configure"),
        see_all=_flag("see_all"),
        folder_see_all=_flag("folder_see_all"),
        contact_groups=_names("contact_groups"),
        commands=_names("commands"),
        map_owner=map_owner,
        map_name=map_name,
    )


# ``LocalSecret.regenerate`` always writes 32 bytes; anything else is a rewrite in progress.
_SITE_SECRET_SIZE = 32


@functools.lru_cache(maxsize=1)
def _site_hmac_for_file(_key: tuple[int, int, int]) -> HmacFn:
    # Read-only on purpose: ``SiteInternalSecret()`` writes its own secret into an
    # empty file, racing omd's rewrite.
    try:
        value = paths.site_internal_secret_file.read_bytes()
    except OSError as exc:
        raise InvalidTicket("site-internal secret is not readable") from exc
    if len(value) != _SITE_SECRET_SIZE:
        raise InvalidTicket("site-internal secret is being rotated")
    # Same HMAC-SHA256 as ``cmk.crypto.secrets.Secret.hmac``, which the GUI signs with.
    return functools.partial(hmac.digest, value, digest="sha256")


def _site_hmac() -> HmacFn:
    """HMAC with the site-internal secret, cached across routes and SSE ticks until the file changes.

    Keyed on inode, mtime and size: omd truncates and rewrites the file in place,
    usually within one coarse mtime tick.
    """
    try:
        st = paths.site_internal_secret_file.stat()
    except OSError as exc:
        raise InvalidTicket("site-internal secret is not readable") from exc
    return _site_hmac_for_file((st.st_ino, st.st_mtime_ns, st.st_size))


def _principal_from_claims(data: dict[str, object]) -> Principal:
    sub = data.get("sub")
    caps = data.get("caps", {})
    if not isinstance(sub, str) or not sub or not isinstance(caps, dict):
        # An empty ``sub`` would make ``map_key_owner`` fall back to "" and hit
        # the owner-less name-only lookup in ``map_service.get_map`` — reading
        # the first matching map of ANY owner. The GUI never mints an empty sub;
        # reject it defensively so a future minting bug can't open that path.
        raise InvalidTicket("ticket payload has unexpected shape")

    return _principal_from_caps(sub, caps, data.get("map"))


def validate_ticket(token: str, *, now: float | None = None) -> Principal:
    """Validate a signed API ticket (the ``X-Maps-Ticket`` header) → :class:`Principal`.

    The wire format (signature, audience, version, expiry) is checked by
    :func:`cmk.maps.shared.ticket.decode_ticket`; here we only interpret the
    daemon-relevant claims. The API audience is required, so a URL stream token
    presented in the header is rejected. Raises :class:`InvalidTicket` on any
    structural, signature, audience or expiry problem.
    """
    data = decode_ticket(token, _site_hmac(), audience=TICKET_AUDIENCE, now=now)
    return _principal_from_claims(data)


def validate_stream_ticket(token: str, *, now: float | None = None) -> Principal:
    """Validate a signed SSE stream token (the ``?token=`` query param) → :class:`Principal`.

    Same wire check as :func:`validate_ticket`, but the stream audience is
    required — so the reduced-capability URL token is accepted ONLY on the SSE
    endpoint, and an API ticket presented as ``?token=`` is rejected. The token
    carries only the read/scope caps; the daemon's SSE path consumes nothing more.
    """
    data = decode_ticket(token, _site_hmac(), audience=STREAM_TICKET_AUDIENCE, now=now)
    return _principal_from_claims(data)


def verify_map_config(config_b64: str, sig: str, *, owner: str) -> dict[str, object]:
    """Verify a GUI-signed map config and return the parsed JSON object.

    Delegates the signature check to :func:`cmk.maps.shared.ticket.verify_config`:
    the GUI resolved the config from the pagetype store and signed the exact
    bytes (with the map owner folded in), and we verify the same bytes against
    ``owner`` — the ticket's ``map_key_owner`` — so a viewer can't substitute a
    tampered config, nor relay a config signed for a foreign owner, for a shared
    broadcast loop. Raises :class:`InvalidTicket` on any decode, signature or
    JSON problem.
    """
    return verify_config(config_b64, sig, _site_hmac(), owner=owner)
