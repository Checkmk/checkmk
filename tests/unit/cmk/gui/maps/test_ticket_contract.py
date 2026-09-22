#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

"""The GUI↔daemon ticket contract, pinned end to end.

The GUI (:mod:`cmk.maps.gui._tickets`) mints a signed ticket; the daemon
(:mod:`cmk.maps.backend.core.auth`) validates it. The two live in different
components and cannot import each other, so the byte-for-byte payload format
lives in :mod:`cmk.maps.shared.ticket`, which both import. This test mints with
the *real* GUI minter and validates with the *real* daemon validator (sharing
one secret), so any drift fails CI — unlike
``packages/cmk-maps/tests/unit/test_ticket_auth.py``, which re-implements the
encoding on the daemon side only.
"""

import hashlib
import hmac
import time
from collections.abc import Iterator

import pytest

from cmk.ccc.user import UserId
from cmk.gui.logged_in import user as global_user
from cmk.maps.backend.core import auth
from cmk.maps.gui import _tickets
from cmk.maps.shared import ticket as maps_ticket
from cmk.maps.shared.ticket import CommandVerb, MapClaim, TicketCapabilities

_KEY = b"0123456789abcdef0123456789abcdef"


def _caps(
    *,
    may_edit: bool = False,
    configure: bool = False,
    see_all: bool = False,
    folder_see_all: bool = False,
    contact_groups: list[str] | None = None,
    commands: list[CommandVerb] | None = None,
) -> TicketCapabilities:
    """A zero-grant capability set, with only what the calling test pins set."""
    return TicketCapabilities(
        may_edit=may_edit,
        configure=configure,
        see_all=see_all,
        folder_see_all=folder_see_all,
        contact_groups=contact_groups or [],
        publish_all=False,
        publish_to_groups=False,
        publish_to_foreign_groups=False,
        publish_to_sites=False,
        all_contact_groups=[],
        all_sites=[],
        commands=commands or [],
    )


class _FakeSecret:
    def hmac(self, msg: bytes) -> bytes:
        return hmac.new(_KEY, msg, hashlib.sha256).digest()


class _FakeSiteInternalSecret:
    @property
    def secret(self) -> _FakeSecret:
        return _FakeSecret()


@pytest.fixture(name="shared_secret")
def fixture_shared_secret(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Both sides sign/verify with the same site-internal secret in production;
    fake it identically here so the test pins the encoding, not the key."""
    monkeypatch.setattr(_tickets, "SiteInternalSecret", _FakeSiteInternalSecret)
    monkeypatch.setattr(auth, "SiteInternalSecret", _FakeSiteInternalSecret)
    yield


def test_both_sides_route_through_the_shared_wire_protocol() -> None:
    # There is a single implementation of the envelope now: the daemon re-exports
    # the shared exception rather than declaring its own, so a divergent private
    # copy of the aud/version/map-prefix contract can't creep back in.
    assert auth.InvalidTicket is maps_ticket.InvalidTicket


def test_map_scoped_ticket_round_trips(
    shared_secret: None,
    request_context: None,
    with_admin_login: UserId,
) -> None:
    # A map-scoped ticket carries the map's real (owner, name); the daemon keys
    # its shared broadcast loop by that owner, not the viewer.
    token = _tickets.mint_ticket(
        global_user,
        caps=_caps(),
        map_claim=MapClaim(owner="alice", name="shared"),
        now=time.time(),
    )
    principal = auth.validate_ticket(token)
    assert principal.map_owner == "alice"
    assert principal.map_name == "shared"
    assert principal.map_key_owner == "alice"


def test_signed_map_config_round_trips_through_real_signer(shared_secret: None) -> None:
    # The GUI signs a resolved map config; the daemon verifies the exact bytes
    # against the ticket owner. This pins the map-config signing contract across
    # the two components.
    config: dict[str, object] = {"name": "shared", "alias": "Shared", "objects": []}
    signed = _tickets.sign_map_config(config, owner="alice")
    verified = auth.verify_map_config(signed["config_b64"], signed["sig"], owner="alice")
    assert verified == config


def test_tampered_signed_map_config_is_rejected(shared_secret: None) -> None:
    signed = _tickets.sign_map_config({"name": "shared", "alias": "Shared"}, owner="alice")
    tampered = _tickets.sign_map_config({"name": "evil", "alias": "Shared"}, owner="alice")
    # A config swapped under a signature minted for a different config must fail.
    with pytest.raises(auth.InvalidTicket):
        auth.verify_map_config(tampered["config_b64"], signed["sig"], owner="alice")


def test_signed_map_config_for_foreign_owner_is_rejected(shared_secret: None) -> None:
    # A config validly signed for one owner must not verify under a ticket scoped
    # to another owner — the owner is bound into the signature.
    signed = _tickets.sign_map_config({"name": "shared", "alias": "Shared"}, owner="alice")
    with pytest.raises(auth.InvalidTicket):
        auth.verify_map_config(signed["config_b64"], signed["sig"], owner="mallory")


def test_explicit_caps_round_trip_through_real_minter(
    shared_secret: None,
    request_context: None,
    with_admin_login: UserId,
) -> None:
    caps = _caps(
        may_edit=True,
        folder_see_all=True,
        contact_groups=["linux", "db"],
        commands=["acknowledge", "schedule_downtime"],
    )
    token = _tickets.mint_ticket(global_user, caps=caps, now=time.time())

    principal = auth.validate_ticket(token)

    assert principal.name == str(with_admin_login)
    assert principal.may_edit is True
    assert principal.folder_see_all is True
    assert principal.contact_groups == frozenset({"linux", "db"})
    assert principal.may_run_command("acknowledge")
    assert not principal.may_run_command("force_check")
    # see_all=False → the daemon scopes Livestatus to this user.
    assert principal.auth_user == str(with_admin_login)


def test_gathered_admin_caps_round_trip(
    shared_secret: None,
    request_context: None,
    with_admin_login: UserId,
) -> None:
    # The real GUI capability resolution for an admin, baked into a real ticket
    # and validated by the daemon — admins bypass contact-group scoping.
    caps = _tickets.gather_capabilities(global_user)
    principal = auth.validate_ticket(_tickets.mint_ticket(global_user, caps=caps, now=time.time()))
    assert principal.name == str(with_admin_login)
    assert principal.configure is True
    assert principal.see_all is True
    assert principal.auth_user is None


def test_expired_ticket_from_real_minter_is_rejected(
    shared_secret: None,
    request_context: None,
    with_admin_login: UserId,
) -> None:
    stale = time.time() - _tickets.TICKET_TTL_SECONDS - 1
    token = _tickets.mint_ticket(global_user, caps=_caps(), now=stale)
    with pytest.raises(auth.InvalidTicket):
        auth.validate_ticket(token)


def test_stream_token_round_trips_and_is_channel_bound(
    shared_secret: None,
    request_context: None,
    with_admin_login: UserId,
) -> None:
    # The reduced-capability SSE stream token minted by the real GUI validates on
    # the daemon's stream channel...
    map_claim = MapClaim(owner="alice", name="shared")
    stream = _tickets.mint_stream_ticket(global_user, map_claim=map_claim, now=time.time())
    principal = auth.validate_stream_ticket(stream)
    assert principal.name == str(with_admin_login)
    assert principal.map_key_owner == "alice"
    # ...but the two channels are strictly separated: a stream token can't drive
    # the REST API (the access-log-exposed credential is useless there), and the
    # header API ticket isn't accepted as a stream credential.
    with pytest.raises(auth.InvalidTicket):
        auth.validate_ticket(stream)
    api = _tickets.mint_ticket(global_user, caps=_caps(), map_claim=map_claim, now=time.time())
    with pytest.raises(auth.InvalidTicket):
        auth.validate_stream_ticket(api)


def test_stream_token_carries_only_scope_caps(
    shared_secret: None,
    request_context: None,
    with_admin_login: UserId,
) -> None:
    # The URL-borne token must not carry command/publish/edit/configure grants, so
    # a captured token grants no privilege beyond the read scope it already had.
    caps = _tickets.gather_stream_capabilities(global_user)
    assert set(caps) == {"see_all", "folder_see_all", "contact_groups"}
    assert "commands" not in caps
    assert "may_edit" not in caps
    assert "configure" not in caps
