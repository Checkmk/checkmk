#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Maps GUI↔daemon ticket wire protocol — one implementation for both sides.

The Maps daemon does no user/session handling: the GUI (which has the full RBAC
/ 2FA context) mints a short-lived signed *ticket* carrying the user's
pre-resolved capabilities, and the daemon validates it against the shared
site-internal secret. It also signs resolved map configs the same way so the
daemon can trust a config a viewer relays.

The two sides live in different components — ``cmk.maps.gui._tickets`` (mint) and
``cmk.maps.backend.core.auth`` (validate) — and neither may import the other. To
stop the byte-for-byte token/signature format from drifting, both import this
module: it owns the envelope (audience, version, map-signing prefix), the
base64url encoding and the HMAC framing. Each side keeps only its own concern —
the GUI turns RBAC into ``caps``, the daemon turns ``caps`` into a principal.

The HMAC key is Checkmk's site-internal secret; callers pass its ``hmac``
function (``SiteInternalSecret().secret.hmac``) so this module carries no
secret-loading or caching policy of its own.
"""

from __future__ import annotations

import base64
import binascii
import hmac
import json
import time
from collections.abc import Callable, Mapping
from typing import NotRequired, TypedDict

# A function that HMACs a message with the site-internal secret. Both sides pass
# ``SiteInternalSecret().secret.hmac``; taking it as a parameter keeps this
# module free of secret loading/caching.
HmacFn = Callable[[bytes], bytes]


class Choice(TypedDict):
    """An (id, alias) pair the SPA's Access editor offers — a contact group or a site."""

    id: str
    alias: str


class MapClaim(TypedDict):
    """The map a ticket is bound to — the map's REAL owner, never a client value.

    Lets the daemon key its shared broadcast loop by the owner rather than the
    viewer, so every viewer of a published map shares one loop.
    """

    owner: str
    name: str


class StreamCapabilities(TypedDict):
    """The read/scope caps the SSE stream token carries — and nothing more.

    The stream token travels in a query string (``EventSource`` cannot set
    headers) and therefore lands in access logs and proxy caches. Carrying only
    the Livestatus contact scope and the SETUP-folder read scope means a captured
    token grants no more than the read access its bearer already had to the one
    map it is bound to.
    """

    see_all: bool
    folder_see_all: bool
    contact_groups: list[str]


class TicketCapabilities(StreamCapabilities):
    """The full capability set the header-borne API ticket carries.

    The daemon still reads these defensively (they arrive as decoded JSON); this
    type pins what the GUI is expected to produce.
    """

    may_edit: bool
    configure: bool
    publish_all: bool
    publish_to_groups: bool
    publish_to_foreign_groups: bool
    publish_to_sites: bool
    all_contact_groups: list[Choice]
    all_sites: list[Choice]
    commands: list[str]


class StreamTicketClaims(TypedDict):
    """The domain claims of an SSE stream token. Always map-bound."""

    sub: str
    exp: int
    caps: StreamCapabilities
    map: MapClaim


class TicketClaims(TypedDict):
    """The domain claims of the header-borne API ticket.

    ``map`` is absent for the map-list / global phase, before a map is opened.
    """

    sub: str
    exp: int
    caps: TicketCapabilities
    map: NotRequired[MapClaim]


# Bound into every ticket payload (``aud``/``v``) so a blob HMAC'd with the
# shared site-internal secret for another purpose can never be replayed as a
# Maps ticket. Bump ``TICKET_VERSION`` on a breaking payload change.
#
# Two audiences separate the two transport channels, so a token minted for one
# can never be replayed on the other:
#   * ``TICKET_AUDIENCE`` — the full-capability API ticket, carried ONLY in the
#     ``X-Maps-Ticket`` header, never in a URL.
#   * ``STREAM_TICKET_AUDIENCE`` — the reduced-capability SSE stream token,
#     carried as a ``?token=`` query parameter (EventSource can't set headers).
#     A query string lands in access logs / proxy caches, so this token is minted
#     with only the read/scope caps and is bound to a single map; the daemon
#     rejects it on every non-SSE endpoint (audience mismatch → 401), so an
#     access-log capture can neither drive the REST API nor escalate privilege.
TICKET_AUDIENCE = "maps-ticket"
STREAM_TICKET_AUDIENCE = "maps-stream"
TICKET_VERSION = 1

# Domain-separation prefix for map-config signatures: HMAC'd with the SAME
# secret as tickets, so a signed map blob and a ticket have disjoint HMAC
# input spaces and can never be interchanged. ``v2`` folds the map owner into the
# signed input (see :func:`_map_sig_input`); a v1 signature (owner-less) no
# longer verifies, which is fine — the GUI and daemon deploy together and nothing
# signed is persisted.
MAP_SIG_CONTEXT = b"maps-map-config:v2:"


class InvalidTicket(Exception):
    """Raised when a ticket or signed map config is malformed, mis-signed or
    expired."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def _canonical_json(obj: Mapping[str, object]) -> bytes:
    """The canonical byte encoding both sides agree on: compact, key-sorted UTF-8.

    Signatures are computed over these exact bytes, so the encoding must be
    deterministic — the daemon verifies the bytes it received rather than
    re-serialising, but the minting side must produce the same bytes every time.
    """
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def encode_ticket(
    claims: Mapping[str, object], hmac_fn: HmacFn, *, audience: str = TICKET_AUDIENCE
) -> str:
    """Stamp the audience/version envelope onto *claims*, sign it, and return the
    ``<b64url(payload)>.<b64url(sig)>`` token.

    Callers pass only their domain claims (``sub``, ``exp``, ``caps`` and an
    optional ``map``); the version lives here so neither side hardcodes it.
    ``audience`` selects the transport channel (:data:`TICKET_AUDIENCE` for the
    header API ticket, :data:`STREAM_TICKET_AUDIENCE` for the URL stream token) so
    the validator can reject a token presented on the wrong channel.
    """
    payload = _canonical_json({"aud": audience, "v": TICKET_VERSION, **claims})
    return f"{_b64url_encode(payload)}.{_b64url_encode(hmac_fn(payload))}"


def decode_ticket(
    token: str, hmac_fn: HmacFn, *, audience: str = TICKET_AUDIENCE, now: float | None = None
) -> dict[str, object]:
    """Verify a ticket's signature, audience, version and expiry; return its claims.

    ``audience`` is the channel the caller expects; a token minted for a different
    audience is rejected here, so a URL stream token can't be replayed on the REST
    API and vice versa. Raises :class:`InvalidTicket` on any structural, signature,
    audience/version or expiry problem. Interpreting the returned claims (``sub``,
    ``caps``, ``map``) is the caller's job.
    """
    try:
        payload_b64, sig_b64 = token.split(".", 1)
    except ValueError:
        raise InvalidTicket("malformed ticket") from None

    try:
        payload = _b64url_decode(payload_b64)
        signature = _b64url_decode(sig_b64)
    except binascii.Error, ValueError:
        raise InvalidTicket("ticket is not valid base64") from None

    if not hmac.compare_digest(signature, hmac_fn(payload)):
        raise InvalidTicket("bad ticket signature")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise InvalidTicket("ticket payload is not JSON") from None
    if not isinstance(data, dict):
        raise InvalidTicket("ticket payload is not an object")

    if data.get("aud") != audience or data.get("v") != TICKET_VERSION:
        raise InvalidTicket("ticket audience/version mismatch")

    exp = data.get("exp")
    if not isinstance(exp, int):
        raise InvalidTicket("ticket payload has unexpected shape")
    if exp < (time.time() if now is None else now):
        raise InvalidTicket("ticket expired")

    return data


def _map_sig_input(owner: str, payload: bytes) -> bytes:
    """The exact bytes an owner-bound map-config signature is computed over.

    Binds the map ``owner`` into the signed input so a config signed for one owner
    can't be relayed under a ticket scoped to another (defense in depth on top of
    the daemon keying the loop by the ticket's owner). ``owner`` is JSON-encoded
    (quoted, escaped) so it delimits unambiguously from the payload — a username
    containing the separator can't shift the owner/config boundary.
    """
    return MAP_SIG_CONTEXT + json.dumps(owner).encode("utf-8") + b"." + payload


def sign_config(config: Mapping[str, object], hmac_fn: HmacFn, *, owner: str) -> dict[str, str]:
    """Sign a resolved map config so the daemon can trust bytes a viewer relays.

    Serialises the config canonically and signs those exact bytes (with the map
    ``owner`` folded in, see :func:`_map_sig_input`) under the map-config
    domain prefix. The relayed ``{config_b64, sig}`` is verified with
    :func:`verify_config` against the owner the daemon resolved from the ticket,
    so a viewer can't substitute a tampered config for a foreign map.
    """
    payload = _canonical_json(config)
    return {
        "config_b64": _b64url_encode(payload),
        "sig": _b64url_encode(hmac_fn(_map_sig_input(owner, payload))),
    }


def verify_config(config_b64: str, sig: str, hmac_fn: HmacFn, *, owner: str) -> dict[str, object]:
    """Verify a signed map config and return the parsed object.

    ``owner`` is the map owner the caller resolved independently (the daemon uses
    the ticket's ``map_key_owner``); it must match the owner the config was
    signed for or the signature check fails. Raises :class:`InvalidTicket` on any
    decode, signature or JSON problem.
    """
    try:
        payload = _b64url_decode(config_b64)
        signature = _b64url_decode(sig)
    except binascii.Error, ValueError:
        raise InvalidTicket("map config is not valid base64") from None

    if not hmac.compare_digest(signature, hmac_fn(_map_sig_input(owner, payload))):
        raise InvalidTicket("bad map config signature")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise InvalidTicket("map config is not JSON") from None
    if not isinstance(data, dict):
        raise InvalidTicket("map config is not an object")
    return data
