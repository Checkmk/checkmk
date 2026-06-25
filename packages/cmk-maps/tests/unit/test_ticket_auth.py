#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Daemon-side validation of the Maps ticket.

The GUI↔daemon contract is pinned end to end with the *real* minter in
``tests/unit/cmk/gui/maps/test_ticket_contract.py`` (which needs a Flask app
context). This file focuses on the daemon's validation edge cases — tampered,
expired, malformed, wrong-audience/version tickets — using a self-contained
``_mint`` so it needs no GUI context. ``_mint`` mirrors the shared encoder's
wire format byte-for-byte; ``test_mint_mirror_matches_shared_encoder`` pins that
against ``encode_ticket`` so the negative cases can't drift onto a stale format.
"""

import base64
import hashlib
import hmac
import json
import time

import pytest

from cmk.maps.backend.core.auth import (
    InvalidTicket,
    validate_stream_ticket,
    validate_ticket,
    verify_map_config,
)
from cmk.maps.shared.ticket import (
    encode_ticket,
    MAP_SIG_CONTEXT,
    sign_config,
    STREAM_TICKET_AUDIENCE,
    TICKET_AUDIENCE,
)

pytestmark = pytest.mark.usefixtures("_shared_secret")

_KEY = b"0123456789abcdef0123456789abcdef"


class _FakeSecret:
    def hmac(self, msg: bytes) -> bytes:
        return hmac.new(_KEY, msg, hashlib.sha256).digest()


class _FakeSiteInternalSecret:
    @property
    def secret(self) -> _FakeSecret:
        return _FakeSecret()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _mint(
    sub: str,
    caps: dict[str, object],
    *,
    exp: int,
    aud: str = "maps-ticket",
    version: int = 1,
    map_claim: dict[str, str] | None = None,
) -> str:
    """Mirror of cmk.maps.gui._tickets.mint_ticket's encoding."""
    claims: dict[str, object] = {"aud": aud, "v": version, "sub": sub, "exp": exp, "caps": caps}
    if map_claim is not None:
        claims["map"] = map_claim
    payload = json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(_KEY, payload, hashlib.sha256).digest()
    return f"{_b64url(payload)}.{_b64url(signature)}"


@pytest.fixture
def _shared_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.maps.backend.core.auth.SiteInternalSecret", _FakeSiteInternalSecret, raising=True
    )


def test_mint_mirror_matches_shared_encoder() -> None:
    # The negative tests below (tamper / expiry / wrong version) are only as
    # strong as ``_mint`` staying byte-identical to the real encoder. Pin the
    # mirror against ``encode_ticket`` directly so a format change there can't
    # leave ``_mint`` — and every negative case built on it — asserting against
    # a stale wire format that no longer exists in production.
    hmac_fn = _FakeSecret().hmac
    exp = 1_700_000_000
    caps: dict[str, object] = {"may_edit": True, "commands": ["acknowledge"]}
    assert _mint("alice", caps, exp=exp) == encode_ticket(
        {"sub": "alice", "exp": exp, "caps": caps}, hmac_fn
    )
    map_claim = {"owner": "alice", "name": "shared"}
    assert _mint("bob", caps, exp=exp, map_claim=map_claim) == encode_ticket(
        {"sub": "bob", "exp": exp, "caps": caps, "map": map_claim}, hmac_fn
    )


def test_roundtrip_resolves_capabilities() -> None:
    caps: dict[str, object] = {
        "may_edit": True,
        "configure": False,
        "see_all": True,
        "folder_see_all": False,
        "contact_groups": ["linux", "db"],
        "commands": ["acknowledge"],
    }
    principal = validate_ticket(_mint("alice", caps, exp=int(time.time()) + 300))
    assert principal.name == "alice"
    assert principal.may_edit is True
    assert principal.see_all is True
    assert principal.contact_groups == frozenset({"linux", "db"})
    assert principal.may_run_command("acknowledge") is True
    # general.see_all → no Livestatus AuthUser scoping.
    assert principal.auth_user is None


def test_scoped_user_has_auth_user() -> None:
    principal = validate_ticket(_mint("bob", {"see_all": False}, exp=int(time.time()) + 300))
    assert principal.auth_user == "bob"
    assert principal.may_edit is False


def test_expired_ticket_rejected() -> None:
    with pytest.raises(InvalidTicket):
        validate_ticket(_mint("alice", {}, exp=int(time.time()) - 1))


def test_tampered_signature_rejected() -> None:
    payload, _, signature = _mint("alice", {}, exp=int(time.time()) + 300).partition(".")
    with pytest.raises(InvalidTicket):
        validate_ticket(f"{payload}.{signature}x")


def test_malformed_token_rejected() -> None:
    with pytest.raises(InvalidTicket):
        validate_ticket("not-a-ticket")


def test_wrong_audience_rejected() -> None:
    # A correctly-signed blob with a different audience (e.g. another component
    # reusing the site-internal secret) must not validate as a Maps ticket.
    with pytest.raises(InvalidTicket):
        validate_ticket(_mint("alice", {}, exp=int(time.time()) + 300, aud="something-else"))


def test_wrong_version_rejected() -> None:
    with pytest.raises(InvalidTicket):
        validate_ticket(_mint("alice", {}, exp=int(time.time()) + 300, version=2))


def test_stream_token_validates_on_stream_channel() -> None:
    map_claim = {"owner": "alice", "name": "shared"}
    principal = validate_stream_ticket(
        _mint(
            "bob",
            {"see_all": False},
            exp=int(time.time()) + 300,
            aud=STREAM_TICKET_AUDIENCE,
            map_claim=map_claim,
        )
    )
    assert principal.name == "bob"
    assert principal.map_key_owner == "alice"
    assert principal.auth_user == "bob"


def test_stream_token_rejected_on_api_channel() -> None:
    # The reduced-capability URL stream token must NOT authenticate a REST call:
    # a token captured from an access log can't be replayed against the API.
    stream = _mint("alice", {}, exp=int(time.time()) + 300, aud=STREAM_TICKET_AUDIENCE)
    with pytest.raises(InvalidTicket):
        validate_ticket(stream)


def test_api_ticket_rejected_on_stream_channel() -> None:
    # Symmetric: the full-capability header ticket is not accepted as a ?token=
    # stream credential, so the audiences stay strictly separated.
    api = _mint("alice", {"configure": True}, exp=int(time.time()) + 300, aud=TICKET_AUDIENCE)
    with pytest.raises(InvalidTicket):
        validate_stream_ticket(api)


def test_map_claim_populates_principal() -> None:
    principal = validate_ticket(
        _mint("bob", {}, exp=int(time.time()) + 300, map_claim={"owner": "alice", "name": "shared"})
    )
    # A map-scoped ticket carries the map's REAL owner so the daemon keys the
    # shared broadcast loop by it, not by the viewer.
    assert principal.map_owner == "alice"
    assert principal.map_name == "shared"
    assert principal.map_key_owner == "alice"


def test_no_map_claim_keys_by_caller() -> None:
    principal = validate_ticket(_mint("bob", {}, exp=int(time.time()) + 300))
    assert principal.map_owner is None
    assert principal.map_key_owner == "bob"


def test_builtin_map_keys_by_empty_owner_not_caller() -> None:
    # A built-in map's owner is the empty string (UserId.builtin()). It is a real,
    # map-scoped owner: the GUI signs the config under "" and keys the shared
    # loop by it. map_key_owner must return "" here, NOT fall back to the caller
    # ("bob") — else the daemon verifies the config signature against the wrong
    # owner and rejects every built-in map with a 403 "Invalid map signature".
    principal = validate_ticket(
        _mint(
            "bob",
            {},
            exp=int(time.time()) + 300,
            map_claim={"owner": "", "name": "service_problems"},
        )
    )
    assert principal.map_owner == ""
    assert principal.map_key_owner == ""


def _sign_map(owner: str, payload: bytes) -> str:
    # Mirror of shared.ticket._map_sig_input: domain prefix + JSON-encoded owner
    # + "." + canonical payload, so a config signed for one owner can't be relayed
    # under a ticket scoped to another.
    sig_input = MAP_SIG_CONTEXT + json.dumps(owner).encode("utf-8") + b"." + payload
    return _b64url(hmac.new(_KEY, sig_input, hashlib.sha256).digest())


def test_sign_map_mirror_matches_shared_signer() -> None:
    # Symmetric to ``test_mint_mirror_matches_shared_encoder``: the tamper /
    # context-confusion cases below are only as strong as ``_sign_map`` staying
    # byte-identical to the real signer's framing (canonical payload + domain
    # prefix + bound owner). The positive round-trip proves compatibility with the
    # *validator* only; pin the mirror against ``sign_config`` — the encoder the
    # GUI actually relays with — so a framing change there can't leave the negative
    # cases asserting against a stale map-config format.
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
    with pytest.raises(InvalidTicket):
        verify_map_config(_b64url(tampered), sig, owner="alice")


def test_verify_map_config_rejects_foreign_owner() -> None:
    # A config validly signed for one owner must not verify under a ticket scoped
    # to another owner — the owner is bound into the signature, on top of the
    # daemon keying the loop by the ticket's owner.
    payload = json.dumps({"name": "shared"}, separators=(",", ":")).encode("utf-8")
    sig = _sign_map("alice", payload)
    with pytest.raises(InvalidTicket):
        verify_map_config(_b64url(payload), sig, owner="mallory")


def test_verify_map_config_rejects_ticket_context_confusion() -> None:
    # A signature made WITHOUT the map-config domain prefix (e.g. a raw ticket
    # HMAC) must not verify as a map config.
    payload = json.dumps({"name": "shared"}, separators=(",", ":")).encode("utf-8")
    wrong_sig = _b64url(hmac.new(_KEY, payload, hashlib.sha256).digest())
    with pytest.raises(InvalidTicket):
        verify_map_config(_b64url(payload), wrong_sig, owner="alice")
