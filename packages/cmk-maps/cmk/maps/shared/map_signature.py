#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The signature on a map config the GUI resolved — one implementation for both sides.

The SPA relays the config of the map it opened to the daemon, and the daemon
keys one shared broadcast loop per map by its owner. A viewer must not be able
to substitute a tampered config for a foreign map, so the GUI signs the exact
bytes with the site-internal secret and the daemon verifies them.

The two sides live in different components — ``cmk.maps.gui._capabilities``
(sign) and ``cmk.maps.backend.core.auth`` (verify) — and neither may import the
other. Both import this module, so the byte-for-byte format cannot drift.

Callers pass the ``hmac`` function of the site-internal secret
(``SiteInternalSecret().secret.hmac``), so this module carries no
secret-loading or caching policy of its own.
"""

import base64
import binascii
import hmac
import json
from collections.abc import Callable, Mapping

# A function that HMACs a message with the site-internal secret.
HmacFn = Callable[[bytes], bytes]

# Domain-separation prefix: the site-internal secret signs other things too, so a
# map-config signature has an input space of its own. ``v2`` folds the map owner
# into the signed input (see :func:`_map_sig_input`); ``v3`` signs only versions
# the GUI set, which the daemon orders saves by.
MAP_SIG_CONTEXT = b"maps-map-config:v3:"


class InvalidSignature(Exception):
    """Raised when a signed map config is malformed or mis-signed."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def _canonical_json(obj: Mapping[str, object]) -> bytes:
    """The canonical byte encoding: compact, key-sorted UTF-8.

    The daemon verifies the bytes it received rather than re-serialising, but
    the signing side must produce the same bytes every time.
    """
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _map_sig_input(owner: str, payload: bytes) -> bytes:
    """The exact bytes an owner-bound map-config signature is computed over.

    Binds the map ``owner`` into the signed input so a config signed for one owner
    can't be relayed under another. ``owner`` is JSON-encoded (quoted, escaped) so
    it delimits unambiguously from the payload — a username containing the
    separator can't shift the owner/config boundary.
    """
    return MAP_SIG_CONTEXT + json.dumps(owner).encode("utf-8") + b"." + payload


def sign_config(config: Mapping[str, object], hmac_fn: HmacFn, *, owner: str) -> dict[str, str]:
    """Sign a resolved map config so the daemon can trust bytes a viewer relays."""
    payload = _canonical_json(config)
    return {
        "config_b64": _b64url_encode(payload),
        "sig": _b64url_encode(hmac_fn(_map_sig_input(owner, payload))),
    }


def verify_config(config_b64: str, sig: str, hmac_fn: HmacFn, *, owner: str) -> dict[str, object]:
    """Verify a signed map config and return the parsed object.

    ``owner`` is the map owner the caller resolved independently (the daemon asks
    the GUI); it must match the owner the config was signed for or the signature
    check fails.
    """
    try:
        payload = _b64url_decode(config_b64)
        signature = _b64url_decode(sig)
    except binascii.Error, ValueError:
        raise InvalidSignature("map config is not valid base64") from None

    if not hmac.compare_digest(signature, hmac_fn(_map_sig_input(owner, payload))):
        raise InvalidSignature("bad map config signature")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise InvalidSignature("map config is not JSON") from None
    if not isinstance(data, dict):
        raise InvalidSignature("map config is not an object")
    return data
