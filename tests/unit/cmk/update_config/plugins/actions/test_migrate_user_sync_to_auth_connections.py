#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the ``user_sync`` → ``authentication_connections`` /
``user_attribute_sync_connections`` migration."""

from cmk.update_config.plugins.actions.migrate_user_sync_to_auth_connections import (
    _derive_new_values,
    _MISSING,
)


def test_legacy_all_on_central_migrates_to_all_types() -> None:
    """Legacy ``"all"`` implied "every LDAP connection, including ones added
    later"; SAML connections already authenticated on the central site before
    the upgrade, so the central enables both connection types."""
    auth, attr = _derive_new_values("all", is_central_site=True, saml_supported=True)
    assert auth == ("all", ["ldap", "saml"])
    assert attr == "all"


def test_legacy_all_on_central_without_distributed_saml() -> None:
    """Editions without per-site SAML don't offer the SAML type."""
    auth, attr = _derive_new_values("all", is_central_site=True, saml_supported=False)
    assert auth == ("all", ["ldap"])
    assert attr == "all"


def test_legacy_all_on_remote_enables_ldap_type_only() -> None:
    """Before the upgrade SAML connections only authenticated on the central
    site, so a remote never enables the SAML type. The attribute sync keeps
    ``"all"`` — its value space is LDAP-only anyway."""
    auth, attr = _derive_new_values("all", is_central_site=False, saml_supported=True)
    assert auth == ("all", ["ldap"])
    assert attr == "all"


def test_legacy_master_on_central_migrates_to_all_types() -> None:
    auth, attr = _derive_new_values("master", is_central_site=True, saml_supported=True)
    assert auth == ("all", ["ldap", "saml"])
    assert attr == "all"


def test_legacy_master_on_remote_disables_both_fields() -> None:
    """``"master"`` on a remote = the central syncs, the remote does not —
    like the explicit "disabled" choice on both fields."""
    auth, attr = _derive_new_values("master", is_central_site=False, saml_supported=True)
    assert auth == "disabled"
    assert attr == "disabled"


def test_legacy_list_migrates_to_plain_lists() -> None:
    """The explicit ``("list", [conn_ids])`` legacy form becomes a plain
    list of LDAP entries for auth and a plain list of connection IDs for
    attribute sync — no tuple wrappers."""
    auth, attr = _derive_new_values(
        ("list", ["ldap_a", "ldap_b"]), is_central_site=False, saml_supported=True
    )
    assert auth == [("ldap", "ldap_a"), ("ldap", "ldap_b")]
    assert attr == ["ldap_a", "ldap_b"]


def test_legacy_none_on_central_disables_both_fields() -> None:
    """Explicit ``user_sync = None`` was the legacy "Disable automatic user
    synchronization" choice; both new fields mirror it as explicitly
    disabled."""
    auth, attr = _derive_new_values(None, is_central_site=True, saml_supported=True)
    assert auth == "disabled"
    assert attr == "disabled"


def test_legacy_none_on_remote_disables_both_fields() -> None:
    auth, attr = _derive_new_values(None, is_central_site=False, saml_supported=True)
    assert auth == "disabled"
    assert attr == "disabled"


def test_missing_user_sync_key_writes_both_fields_explicitly() -> None:
    """A hand-edited site spec without the ``user_sync`` key: both values
    are written explicitly (an absent key now falls back to the "all"
    defaults, which would enroll SAML connections on a remote and start the
    attribute sync there). Authentication preserves that LDAP login always
    worked; the attribute sync follows the legacy ``userdb_automatic_sync``
    default ("master": only the central site syncs)."""
    auth, attr = _derive_new_values(_MISSING, is_central_site=False, saml_supported=True)
    assert auth == ("all", ["ldap"])
    assert attr == "disabled"

    auth, attr = _derive_new_values(_MISSING, is_central_site=True, saml_supported=True)
    assert auth == ("all", ["ldap", "saml"])
    assert attr == "all"
