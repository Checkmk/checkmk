#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the ``user_sync`` → ``authentication_connections`` /
``user_attribute_sync_connections`` migration."""

from cmk.update_config.plugins.actions.migrate_user_sync_to_auth_connections import (
    _derive_new_values,
)


def test_legacy_all_sets_attr_sync_only() -> None:
    """Legacy ``"all"`` is migrated to attribute-sync only; authentication
    connections must be picked explicitly by the admin (key absent)."""
    auth, attr = _derive_new_values("all", is_central_site=False)
    assert auth is None
    assert attr == "all"


def test_legacy_master_on_central_sets_attr_sync_only() -> None:
    auth, attr = _derive_new_values("master", is_central_site=True)
    assert auth is None
    assert attr == "all"


def test_legacy_master_on_remote_leaves_both_unset() -> None:
    """``"master"`` on a remote = the central syncs, the remote does not.
    Both new fields are left unset so the remote inherits from the
    central."""
    auth, attr = _derive_new_values("master", is_central_site=False)
    assert auth is None
    assert attr is None


def test_legacy_list_migrates_to_plain_lists() -> None:
    """The explicit ``("list", [conn_ids])`` legacy form becomes a plain
    list of LDAP entries for auth and a plain list of connection IDs for
    attribute sync — no tuple wrappers."""
    auth, attr = _derive_new_values(("list", ["ldap_a", "ldap_b"]), is_central_site=False)
    assert auth == [("ldap", "ldap_a"), ("ldap", "ldap_b")]
    assert attr == ["ldap_a", "ldap_b"]


def test_unknown_user_sync_value_leaves_both_unset() -> None:
    auth, attr = _derive_new_values(None, is_central_site=False)
    assert auth is None
    assert attr is None
