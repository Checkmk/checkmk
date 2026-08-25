#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for user identity unification across connectors (CMK-33805).

These cover the credential-resolution layer (`cmk.gui.userdb._check_credentials`)
that is meant to resolve a user reaching Checkmk through more than one connector
to a *single* record — no duplicate account created by the second connector.

The credential resolver also implements the CMK-33822 connector-reordering
rule: when a user is already owned by one connector, ``check_credentials``
consults that *owning* connector first -- even if it is declared last -- so
the user is resolved by their own connector and the second connector never
claims them.
"""

from collections.abc import Sequence
from datetime import datetime

import pytest

from cmk.ccc.user import UserId
from cmk.crypto.password import Password
from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb import _check_credentials, new_user_template

_NOW = datetime(2026, 6, 8, 12, 0, 0)


def _default_profile() -> UserSpec:
    """A fresh default profile per call.

    `new_user_template` merges the profile into the new record with a shallow
    `update`, so a single shared instance would hand every created user the
    *same* `roles`/`contactgroups` list objects — one test mutating them would
    leak into the next.
    """
    return UserSpec(contactgroups=[], roles=["user"], force_authuser=False)


class _FakeConnector:
    """A minimal stand-in for a `UserConnector` whose `check_credentials` result
    is whatever the test wants. Records whether it was consulted."""

    def __init__(self, connector_id: str, result: object) -> None:
        self._id = connector_id
        self._result = result
        self.consulted = False

    def type(self) -> str:
        return self._id

    def check_credentials(self, *_args: object, **_kwargs: object) -> object:
        self.consulted = True
        return self._result


def _patch_resolution(
    monkeypatch: pytest.MonkeyPatch,
    *,
    connectors: Sequence[tuple[str, _FakeConnector]],
    existing: bool,
    owning_connector: str | None = None,
) -> dict[str, int]:
    """Wire up `_check_credentials` so `check_credentials` runs without a real
    site: a fixed connector chain, a known `user_exists` answer, and recording
    stubs for the user-store mutators. Returns a dict counting store writes.

    The connector chain is injected by stubbing `active_connections` (the
    production code calls it with the `user_connections` argument); `pprint_value`
    and `debug` are plain parameters of `check_credentials`/`_create_non_existing_user`
    now, so the tests need no request context or `active_config` proxy."""
    calls = {"save_users": 0, "load_users": 0, "do_sync": 0}

    monkeypatch.setattr(_check_credentials, "active_connections", lambda _cfg: list(connectors))
    # CMK-33822: the connector that already owns the user is consulted first.
    # By default no owner is known (returns None), so declaration order holds.
    monkeypatch.setattr(_check_credentials, "_connection_id_of_user", lambda _u: owning_connector)
    monkeypatch.setattr(_check_credentials, "user_exists", lambda _u: existing)
    monkeypatch.setattr(_check_credentials, "load_user", lambda _u: UserSpec(roles=["user"]))
    monkeypatch.setattr(
        _check_credentials, "is_customer_user_allowed_to_login", lambda _u, _s: True
    )
    monkeypatch.setattr(_check_credentials, "user_locked", lambda _u, _s: False)

    def _load_users(lock: bool = False) -> dict[UserId, UserSpec]:
        calls["load_users"] += 1
        return {}

    def _save_users(*_args: object, **_kwargs: object) -> None:
        calls["save_users"] += 1

    monkeypatch.setattr(_check_credentials, "load_users", _load_users)
    monkeypatch.setattr(_check_credentials, "save_users", _save_users)

    # `_create_non_existing_user` looks the connection up again for the post-
    # creation sync hook. Return a stub whose `do_sync` is recorded, so the
    # create path runs to completion instead of falling into the error branch
    # (which would touch the `html` request-context proxy).
    class _FakeConnection:
        def type(self) -> str:
            return "ldap"

        def do_sync(self, *_args: object, **_kwargs: object) -> None:
            calls["do_sync"] += 1

    monkeypatch.setattr(_check_credentials, "get_connection", lambda _cid: _FakeConnection())
    monkeypatch.setattr(_check_credentials, "log_security_event", lambda _e: None)
    return calls


def test_create_non_existing_user_is_noop_when_user_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`_create_non_existing_user` must short-circuit on `user_exists`
    so a second connector neither overwrites nor duplicates the record."""
    calls = _patch_resolution(monkeypatch, connectors=[], existing=True)

    _check_credentials._create_non_existing_user(
        "saml2", UserId("bob"), [], [], _NOW, _default_profile(), pprint_value=False, debug=False
    )

    assert calls["save_users"] == 0
    assert calls["load_users"] == 0


def test_create_non_existing_user_creates_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative/mutation guard: when the user does *not* exist, the
    record is created — proving the no-op above is genuinely gated on
    `user_exists`, not always skipping."""
    calls = _patch_resolution(monkeypatch, connectors=[], existing=False)

    _check_credentials._create_non_existing_user(
        "ldap", UserId("carol"), [], [], _NOW, _default_profile(), pprint_value=False, debug=False
    )

    assert calls["save_users"] == 1
    # the freshly created user is handed to the connector's sync hook
    assert calls["do_sync"] == 1


def test_check_credentials_stops_at_first_matching_connector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Once a connector returns a `UserId`, later connectors are not
    consulted — two enabled connectors never both create the same user."""
    first = _FakeConnector("saml2", result=UserId("dave"))
    second = _FakeConnector("ldap", result=UserId("dave"))
    _patch_resolution(monkeypatch, connectors=[("saml2", first), ("ldap", second)], existing=True)

    result = _check_credentials.check_credentials(
        UserId("dave"),
        Password("pw"),
        [],
        [],
        _NOW,
        _default_profile(),
        pprint_value=False,
        debug=False,
    )

    assert result == UserId("dave")
    assert first.consulted is True
    assert second.consulted is False


def test_unknown_user_falls_through_to_next_connector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative: a connector returning `None` (user unknown) does not
    stop the chain; the next connector is consulted."""
    first = _FakeConnector("saml2", result=None)
    second = _FakeConnector("ldap", result=UserId("erin"))
    _patch_resolution(monkeypatch, connectors=[("saml2", first), ("ldap", second)], existing=True)

    result = _check_credentials.check_credentials(
        UserId("erin"),
        Password("pw"),
        [],
        [],
        _NOW,
        _default_profile(),
        pprint_value=False,
        debug=False,
    )

    assert result == UserId("erin")
    assert first.consulted is True
    assert second.consulted is True


def test_owning_connector_is_consulted_first_even_when_declared_last(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CMK-33822 reordering: when a user is already owned by one
    connector, that owning connector is consulted *first* during credential
    resolution -- even if it is declared last. So the owning connector resolves
    the user and the connector declared first never claims them."""
    # Declaration order: saml2 first, ldap last. The user is owned by ldap.
    saml = _FakeConnector("saml2", result=UserId("grace"))
    ldap = _FakeConnector("ldap", result=UserId("grace"))
    _patch_resolution(
        monkeypatch,
        connectors=[("saml2", saml), ("ldap", ldap)],
        existing=True,
        owning_connector="ldap",
    )

    result = _check_credentials.check_credentials(
        UserId("grace"),
        Password("pw"),
        [],
        [],
        _NOW,
        _default_profile(),
        pprint_value=False,
        debug=False,
    )

    assert result == UserId("grace")
    # The owning connector (declared last) wins; the first-declared one is never
    # reached because resolution stops at the first matching connector.
    assert ldap.consulted is True
    assert saml.consulted is False


def test_without_owner_match_declaration_order_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CMK-33822 reordering, mutation guard: with no known owning
    connector (``_connection_id_of_user`` returns ``None``), the reordering is a
    no-op and connectors are consulted in declaration order -- so the *first*
    declared connector resolves the user. This pins that the reordering only
    fires for the actual owner, not unconditionally."""
    saml = _FakeConnector("saml2", result=UserId("heidi"))
    ldap = _FakeConnector("ldap", result=UserId("heidi"))
    _patch_resolution(
        monkeypatch,
        connectors=[("saml2", saml), ("ldap", ldap)],
        existing=True,
        owning_connector=None,
    )

    result = _check_credentials.check_credentials(
        UserId("heidi"),
        Password("pw"),
        [],
        [],
        _NOW,
        _default_profile(),
        pprint_value=False,
        debug=False,
    )

    assert result == UserId("heidi")
    # Declaration order holds: the first connector resolves it, the second is
    # never consulted.
    assert saml.consulted is True
    assert ldap.consulted is False


def test_login_via_second_connector_resolves_to_existing_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A user who already exists under one connector and authenticates through
    another is resolved to that same record, and nothing is written.

    The end-to-end shape of the unification guarantee: the owning connector
    (consulted first) cannot verify these credentials and returns ``None``, so
    the chain falls through to the second connector, which authenticates the
    user. The returned id is the existing one and no user record is created or
    synced -- the second connector neither forks a duplicate nor claims the
    record during login."""
    owner = _FakeConnector("saml2", result=None)
    other = _FakeConnector("ldap", result=UserId("ivan"))
    calls = _patch_resolution(
        monkeypatch,
        connectors=[("saml2", owner), ("ldap", other)],
        existing=True,
        owning_connector="saml2",
    )

    result = _check_credentials.check_credentials(
        UserId("ivan"),
        Password("pw"),
        [],
        [],
        _NOW,
        _default_profile(),
        pprint_value=False,
        debug=False,
    )

    assert result == UserId("ivan")
    assert owner.consulted is True
    assert other.consulted is True
    # No second record: the create path short-circuits on the existing user.
    assert calls["save_users"] == 0
    assert calls["do_sync"] == 0


def test_orphaned_owning_connector_denies_login_without_creating_a_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A user whose owning connection has been deleted cannot log in, and is
    not silently re-provisioned under whatever connector answers next.

    Deleting a connection does not rewrite the users it owns, so their
    ``connector`` keeps naming a connection that is no longer configured. That
    id is absent from ``active_connections``, so the owner-first reordering has
    nothing to hoist and every remaining connector is asked in declaration
    order. None of them knows the user -- an LDAP/SAML-owned user has no
    htpasswd hash to fall back on (see
    ``tests/unit/cmk/gui/test_userdb_htpasswd_connector.py``) -- so resolution
    runs off the end of the chain and denies the login.

    The account must also survive: returning ``False`` rather than creating a
    fresh record is what keeps the user recoverable by re-adding the
    connection, instead of leaving a duplicate owned by the wrong connector.
    """
    htpasswd_connector = _FakeConnector("htpasswd", result=None)
    calls = _patch_resolution(
        monkeypatch,
        connectors=[("htpasswd", htpasswd_connector)],
        existing=True,
        owning_connector="ldap_deleted",
    )

    result = _check_credentials.check_credentials(
        UserId("judy"),
        Password("pw"),
        [],
        [],
        _NOW,
        _default_profile(),
        pprint_value=False,
        debug=False,
    )

    assert result is False, (
        "a user whose owning connection was deleted must not be authenticated by another connector"
    )
    assert htpasswd_connector.consulted is True, (
        "the orphaned owner id must not abort the chain -- the remaining "
        "connectors still get their turn"
    )
    assert calls["save_users"] == 0, "a denied login must not re-provision the user record"


def test_new_user_template_stamps_single_owning_connector() -> None:
    """A freshly provisioned user carries exactly the creating
    connector id, so a new record has one unambiguous owner."""
    template = new_user_template("ldap_corp", _default_profile())

    assert template["connector"] == "ldap_corp"
    # default profile is merged in without clobbering the connector
    assert template["roles"] == ["user"]
