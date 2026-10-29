#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Daemon-side verification of a GUI-signed map config.

The GUI↔daemon contract is pinned end to end with the *real* signer in
``tests/unit/cmk/gui/maps/test_map_signature_contract.py`` (which needs the GUI).
This file focuses on the daemon's verification edge cases using a self-contained
``_sign_map``, which ``test_sign_map_mirror_matches_shared_signer`` pins against
the shared signer so the negative cases can't drift onto a stale format.
"""

import base64
import hashlib
import hmac
import json
from pathlib import Path

import pytest

from cmk.maps.backend.core.auth import InvalidSignature, verify_map_config
from cmk.maps.shared.map_signature import MAP_SIG_CONTEXT, sign_config

pytestmark = pytest.mark.usefixtures("_shared_secret")

_KEY = b"0123456789abcdef0123456789abcdef"


class _FakeSecret:
    def hmac(self, msg: bytes) -> bytes:
        return hmac.new(_KEY, msg, hashlib.sha256).digest()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


@pytest.fixture
def _shared_secret(site_secret_file: Path) -> None:
    site_secret_file.write_bytes(_KEY)


def _sign_map(owner: str, payload: bytes) -> str:
    # Mirror of shared.map_signature._map_sig_input: domain prefix + JSON-encoded
    # owner + "." + canonical payload.
    sig_input = MAP_SIG_CONTEXT + json.dumps(owner).encode("utf-8") + b"." + payload
    return _b64url(hmac.new(_KEY, sig_input, hashlib.sha256).digest())


def test_sign_map_mirror_matches_shared_signer() -> None:
    # The tamper / context-confusion cases below are only as strong as
    # ``_sign_map`` staying byte-identical to the real signer's framing (canonical
    # payload + domain prefix + bound owner).
    hmac_fn = _FakeSecret().hmac
    config = {"name": "shared", "alias": "S"}
    payload = json.dumps(config, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signed = sign_config(config, hmac_fn, owner="alice")
    assert signed["config_b64"] == _b64url(payload)
    assert signed["sig"] == _sign_map("alice", payload)


def test_verify_map_config_accepts_valid_signature() -> None:
    payload = json.dumps({"name": "shared", "alias": "S"}, separators=(",", ":")).encode("utf-8")
    result = verify_map_config(_b64url(payload), _sign_map("alice", payload), owner="alice")
    assert result == {"name": "shared", "alias": "S"}


def test_verify_map_config_rejects_tampered_config() -> None:
    payload = json.dumps({"name": "shared"}, separators=(",", ":")).encode("utf-8")
    sig = _sign_map("alice", payload)
    tampered = json.dumps({"name": "evil"}, separators=(",", ":")).encode("utf-8")
    with pytest.raises(InvalidSignature):
        verify_map_config(_b64url(tampered), sig, owner="alice")


def test_verify_map_config_rejects_foreign_owner() -> None:
    # A config validly signed for one owner must not verify under the owner the
    # GUI named for the map — the owner is bound into the signature.
    payload = json.dumps({"name": "shared"}, separators=(",", ":")).encode("utf-8")
    sig = _sign_map("alice", payload)
    with pytest.raises(InvalidSignature):
        verify_map_config(_b64url(payload), sig, owner="mallory")


def test_verify_map_config_rejects_context_confusion() -> None:
    # A signature made WITHOUT the map-config domain prefix (another use of the
    # site secret) must not verify as a map config.
    payload = json.dumps({"name": "shared"}, separators=(",", ":")).encode("utf-8")
    wrong_sig = _b64url(hmac.new(_KEY, payload, hashlib.sha256).digest())
    with pytest.raises(InvalidSignature):
        verify_map_config(_b64url(payload), wrong_sig, owner="alice")
