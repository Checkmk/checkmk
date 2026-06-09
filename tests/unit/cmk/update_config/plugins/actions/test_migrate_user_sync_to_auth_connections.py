#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the ``user_sync`` → ``authentication_connections`` /
``user_attribute_sync_connections`` migration."""

import logging
from types import SimpleNamespace

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.watolib.sites import (
    _auth_connections_from_disk,
    _auth_connections_to_disk,
    _user_attribute_sync_from_disk,
    _user_attribute_sync_to_disk,
)
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions import (
    migrate_user_sync_to_auth_connections as mod,
)
from cmk.update_config.plugins.actions.migrate_user_sync_to_auth_connections import (
    _derive_new_values,
    _MISSING,
    MigrateUserSyncToAuthConnections,
)
from tests.unit.cmk.update_config.plugins.actions.site_mgmt_fakes import FakeSiteMgmt

_LOGGER = logging.getLogger("test")
_CENTRAL = SiteId("central")


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


def test_legacy_empty_list_disables_both_fields() -> None:
    auth, attr = _derive_new_values(("list", []), is_central_site=True, saml_supported=True)
    assert auth == "disabled"
    assert attr == "disabled"


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


@pytest.mark.parametrize(
    "legacy_user_sync, is_central_site",
    [
        ("all", True),
        ("all", False),
        ("master", True),
        ("master", False),
        (("list", ["ldap_a", "ldap_b"]), False),
        (None, False),
        (_MISSING, True),
        (_MISSING, False),
    ],
)
def test_migrated_legacy_values_feed_ported_form_spec_without_diff(
    legacy_user_sync: object, is_central_site: bool
) -> None:
    """The "Add connection" half: every migrated legacy ``user_sync`` shape round-trips through the ported Form Spec converters unchanged (SAML half: tests/unit/cmk/gui/nonfree/pro/saml2/test_config.py)."""
    auth_value, attr_sync_value = _derive_new_values(
        legacy_user_sync, is_central_site=is_central_site, saml_supported=True
    )

    assert _auth_connections_to_disk(_auth_connections_from_disk(auth_value)) == auth_value
    assert (
        _user_attribute_sync_to_disk(_user_attribute_sync_from_disk(attr_sync_value))
        == attr_sync_value
    )


def _action() -> MigrateUserSyncToAuthConnections:
    return MigrateUserSyncToAuthConnections(
        name="migrate_user_sync_to_auth_connections",
        title="test",
        sort_index=35,
        expiry_version=ExpiryVersion.CMK_310,
    )


def _run(monkeypatch: pytest.MonkeyPatch, sites: dict[SiteId, dict[str, object]]) -> FakeSiteMgmt:
    fake = FakeSiteMgmt(sites)
    monkeypatch.setattr(mod, "site_management_registry", {"site_management": fake})
    monkeypatch.setattr(mod, "omd_site", lambda: _CENTRAL)
    monkeypatch.setattr(
        mod,
        "active_config",
        SimpleNamespace(wato_pprint_config=False, liveproxyd_enabled=False, wato_use_git=False),
    )
    monkeypatch.setattr(mod, "make_folder_tree", lambda _config: None)
    _action()(_LOGGER)
    return fake


def test_call_migrates_legacy_list_and_preserves_other_site_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``__call__`` derives the new fields from a legacy
    ``("list", [...])`` ``user_sync``, drops the obsolete key, and leaves
    unrelated site-spec fields untouched."""
    sites: dict[SiteId, dict[str, object]] = {
        SiteId("remote1"): {"user_sync": ("list", ["ldap_a"]), "alias": "Remote 1"}
    }
    fake = _run(monkeypatch, sites)

    assert fake.saved is not None  # a site changed, so the map was written
    spec = fake.saved[SiteId("remote1")]
    assert spec["authentication_connections"] == [("ldap", "ldap_a")]
    assert spec["user_attribute_sync_connections"] == ["ldap_a"]
    assert "user_sync" not in spec  # obsolete key removed
    assert spec["alias"] == "Remote 1"  # unrelated field preserved


def test_call_does_not_overwrite_preexisting_new_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A site that already set ``authentication_connections``
    manually keeps it; only the still-unset field is filled, and the legacy
    key is dropped."""
    sites: dict[SiteId, dict[str, object]] = {
        SiteId("remote1"): {
            "user_sync": ("list", ["ldap_a"]),
            "authentication_connections": [("ldap", "manual")],
        }
    }
    fake = _run(monkeypatch, sites)

    assert fake.saved is not None
    spec = fake.saved[SiteId("remote1")]
    assert spec["authentication_connections"] == [("ldap", "manual")]  # not overwritten
    assert spec["user_attribute_sync_connections"] == ["ldap_a"]  # unset field filled
    assert "user_sync" not in spec


def test_call_is_noop_when_already_migrated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Idempotency: a re-run on a site with no ``user_sync`` and
    the new fields already present writes nothing."""
    sites: dict[SiteId, dict[str, object]] = {
        SiteId("remote1"): {
            "authentication_connections": [("ldap", "x")],
            "user_attribute_sync_connections": ["x"],
        }
    }
    fake = _run(monkeypatch, sites)

    assert fake.saved is None  # save_sites never called
