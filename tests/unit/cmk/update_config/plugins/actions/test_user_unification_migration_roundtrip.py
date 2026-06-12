#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Combined round-trip over both user-unification config migrations (CMK-33805).

Running ``MigrateUserSyncToAuthConnections`` and
``RemoveSAMLOwnedBySite`` in sequence preserves every site, every connection,
and all their unrelated fields (no data loss), and the pair is jointly
idempotent — a second run writes nothing and changes nothing. Both actions
operate only on the sites config and the connection config; user records are
never read or written, so user accounts/contact groups/roles are untouched by
construction (the meaningful losslessness here is config-level)."""

from __future__ import annotations

import copy
import logging
from types import SimpleNamespace
from typing import cast

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.user_connection_config_types import ConfigurableUserConnectionSpec
from cmk.gui.userdb import UserConnectionConfigFile
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions import (
    migrate_user_sync_to_auth_connections as migrate_mod,
)
from cmk.update_config.plugins.actions import (
    remove_saml_owned_by_site as remove_mod,
)
from cmk.update_config.plugins.actions.migrate_user_sync_to_auth_connections import (
    MigrateUserSyncToAuthConnections,
)
from cmk.update_config.plugins.actions.remove_saml_owned_by_site import RemoveSAMLOwnedBySite
from tests.unit.cmk.update_config.plugins.actions.site_mgmt_fakes import FakeSiteMgmt

_LOGGER = logging.getLogger("test")
_CENTRAL = SiteId("central")


def _drive(
    monkeypatch: pytest.MonkeyPatch,
    sites: dict[SiteId, dict[str, object]],
    connections: list[dict[str, object]],
) -> tuple[dict[SiteId, dict[str, object]] | None, bool]:
    """Run both migrations once against the (mutable) state, returning whether
    the sites config and the connection config were written."""
    site_mgmt = FakeSiteMgmt(sites)
    monkeypatch.setattr(migrate_mod, "site_management_registry", {"site_management": site_mgmt})
    monkeypatch.setattr(migrate_mod, "omd_site", lambda: _CENTRAL)
    monkeypatch.setattr(
        migrate_mod,
        "active_config",
        SimpleNamespace(wato_pprint_config=False, liveproxyd_enabled=False, wato_use_git=False),
    )
    monkeypatch.setattr(migrate_mod, "make_folder_tree", lambda _config: None)

    conn_saved = {"called": False}
    monkeypatch.setattr(remove_mod, "active_config", SimpleNamespace(wato_pprint_config=False))
    monkeypatch.setattr(
        UserConnectionConfigFile,
        "load_for_modification",
        lambda _self: cast(list[ConfigurableUserConnectionSpec], connections),
    )
    monkeypatch.setattr(
        UserConnectionConfigFile,
        "save",
        lambda _self, _cfg, pprint_value: conn_saved.__setitem__("called", True),
    )

    MigrateUserSyncToAuthConnections(
        name="migrate_user_sync_to_auth_connections",
        title="test",
        sort_index=35,
        expiry_version=ExpiryVersion.CMK_310,
    )(_LOGGER)
    RemoveSAMLOwnedBySite(
        name="remove_saml_owned_by_site",
        title="test",
        sort_index=40,
        expiry_version=ExpiryVersion.CMK_310,
    )(_LOGGER)

    return site_mgmt.saved, conn_saved["called"]


def test_both_migrations_preserve_all_config_and_are_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sites: dict[SiteId, dict[str, object]] = {
        _CENTRAL: {"user_sync": "master", "alias": "Central", "socket": ("local", None)},
        SiteId("remote1"): {"user_sync": ("list", ["ldap_a"]), "alias": "Remote 1"},
        SiteId("remote2"): {
            "authentication_connections": [("ldap", "x")],
            "user_attribute_sync_connections": ["x"],
            "alias": "Remote 2",
        },
    }
    connections: list[dict[str, object]] = [
        {
            "type": "saml2",
            "id": "saml_corp",
            "name": "Corp",
            "owned_by_site": "central",
            "disabled": False,
        },
        {"type": "ldap", "id": "ldap_a", "disabled": False},
        {"type": "saml2", "id": "saml_plain", "name": "Plain"},
    ]

    site_saved, conn_saved = _drive(monkeypatch, sites, connections)

    assert site_saved is not None
    assert conn_saved is True

    assert set(sites) == {_CENTRAL, SiteId("remote1"), SiteId("remote2")}
    assert [conn["id"] for conn in connections] == ["saml_corp", "ldap_a", "saml_plain"]

    assert sites[_CENTRAL]["alias"] == "Central"
    assert sites[_CENTRAL]["socket"] == ("local", None)
    assert sites[SiteId("remote1")]["alias"] == "Remote 1"
    assert sites[SiteId("remote2")]["alias"] == "Remote 2"

    assert "user_sync" not in sites[_CENTRAL]
    assert "user_sync" not in sites[SiteId("remote1")]
    assert sites[_CENTRAL]["user_attribute_sync_connections"] == "all"
    assert sites[SiteId("remote1")]["authentication_connections"] == [("ldap", "ldap_a")]
    assert sites[SiteId("remote1")]["user_attribute_sync_connections"] == ["ldap_a"]
    assert sites[SiteId("remote2")]["authentication_connections"] == [("ldap", "x")]

    assert connections[0] == {"type": "saml2", "id": "saml_corp", "name": "Corp", "disabled": False}
    assert connections[1] == {"type": "ldap", "id": "ldap_a", "disabled": False}
    assert connections[2] == {"type": "saml2", "id": "saml_plain", "name": "Plain"}

    sites_after_first = copy.deepcopy(sites)
    connections_after_first = copy.deepcopy(connections)

    site_saved2, conn_saved2 = _drive(monkeypatch, sites, connections)

    assert site_saved2 is None
    assert conn_saved2 is False
    assert sites == sites_after_first
    assert connections == connections_after_first
