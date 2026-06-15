#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the ``user_sync`` → ``authentication_connections`` /
``user_attribute_sync_connections`` migration."""

from cmk.update_config.plugins.actions.migrate_user_sync_to_auth_connections import (
    _derive_new_values,
)

_LDAP_IDS = ["ldap_a", "ldap_b"]


def test_legacy_all_expands_to_all_ldap_connections() -> None:
    """Legacy ``"all"`` implied "every LDAP connection". It expands into an
    explicit ``authentication_connections`` list of all configured LDAP
    connections so the site keeps creating users after upgrade; attribute sync
    stays ``"all"``."""
    auth, attr = _derive_new_values("all", is_central_site=False, ldap_connection_ids=_LDAP_IDS)
    assert auth == [("ldap", "ldap_a"), ("ldap", "ldap_b")]
    assert attr == "all"


def test_legacy_master_on_central_expands_to_all_ldap_connections() -> None:
    auth, attr = _derive_new_values("master", is_central_site=True, ldap_connection_ids=_LDAP_IDS)
    assert auth == [("ldap", "ldap_a"), ("ldap", "ldap_b")]
    assert attr == "all"


def test_legacy_master_on_remote_leaves_both_unset() -> None:
    """``"master"`` on a remote = the central syncs, the remote does not.
    Both new fields are left unset so the remote inherits from the
    central."""
    auth, attr = _derive_new_values("master", is_central_site=False, ldap_connection_ids=_LDAP_IDS)
    assert auth is None
    assert attr is None


def test_legacy_all_with_no_ldap_connections_yields_empty_auth_list() -> None:
    """With no configured LDAP connections, ``"all"`` expands to an empty
    authentication list (still set, not absent) while attribute sync stays
    ``"all"``."""
    auth, attr = _derive_new_values("all", is_central_site=True, ldap_connection_ids=[])
    assert auth == []
    assert attr == "all"


def test_legacy_list_migrates_to_plain_lists() -> None:
    """The explicit ``("list", [conn_ids])`` legacy form becomes a plain
    list of LDAP entries for auth and a plain list of connection IDs for
    attribute sync — no tuple wrappers. Independent of the configured LDAP
    connections."""
    auth, attr = _derive_new_values(
        ("list", ["ldap_a", "ldap_b"]), is_central_site=False, ldap_connection_ids=["ldap_other"]
    )
    assert auth == [("ldap", "ldap_a"), ("ldap", "ldap_b")]
    assert attr == ["ldap_a", "ldap_b"]


def test_unknown_user_sync_value_leaves_both_unset() -> None:
    auth, attr = _derive_new_values(None, is_central_site=False, ldap_connection_ids=_LDAP_IDS)
    assert auth is None
    assert attr is None
