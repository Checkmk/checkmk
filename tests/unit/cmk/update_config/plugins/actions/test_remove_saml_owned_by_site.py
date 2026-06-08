#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the ``remove_saml_owned_by_site`` update action (CMK-33805).

The action strips the deprecated ``owned_by_site`` attribute from SAML
connections so the on-disk config matches the new schema.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import cast

import pytest

from cmk.gui.user_connection_config_types import ConfigurableUserConnectionSpec
from cmk.gui.userdb import UserConnectionConfigFile
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions import remove_saml_owned_by_site as mod
from cmk.update_config.plugins.actions.remove_saml_owned_by_site import RemoveSAMLOwnedBySite

_LOGGER = logging.getLogger("test")


def _action() -> RemoveSAMLOwnedBySite:
    return RemoveSAMLOwnedBySite(
        name="remove_saml_owned_by_site",
        title="test",
        sort_index=40,
        expiry_version=ExpiryVersion.CMK_310,
    )


def _run(
    monkeypatch: pytest.MonkeyPatch, connections: list[dict[str, object]]
) -> list[dict[str, object]] | None:
    """Drive the action against an in-memory connection list, returning whatever
    it tried to save (or ``None`` if it saved nothing)."""
    saved: dict[str, list[dict[str, object]] | None] = {"cfg": None}

    monkeypatch.setattr(mod, "active_config", SimpleNamespace(wato_pprint_config=False))
    monkeypatch.setattr(
        UserConnectionConfigFile,
        "load_for_modification",
        lambda _self: cast(list[ConfigurableUserConnectionSpec], connections),
    )

    def _save(_self: object, cfg: object, pprint_value: bool) -> None:
        saved["cfg"] = cast(list[dict[str, object]], cfg)

    monkeypatch.setattr(UserConnectionConfigFile, "save", _save)

    _action()(_LOGGER)
    return saved["cfg"]


def test_strips_owned_by_site_keeps_other_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """``owned_by_site`` is removed from a SAML connection while every
    other field survives untouched."""
    conn = {
        "type": "saml2",
        "id": "saml_corp",
        "name": "Corp SAML",
        "owned_by_site": "central",
        "disabled": False,
    }
    saved = _run(monkeypatch, [conn])

    assert saved is not None  # a modification happened, so the file was written
    (result,) = saved
    assert "owned_by_site" not in result
    assert result == {
        "type": "saml2",
        "id": "saml_corp",
        "name": "Corp SAML",
        "disabled": False,
    }


def test_connection_without_key_is_left_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """No-op guard: a SAML connection that never had
    ``owned_by_site`` causes no write at all."""
    conn: dict[str, object] = {"type": "saml2", "id": "saml_plain", "name": "Plain SAML"}
    saved = _run(monkeypatch, [conn])

    assert saved is None  # nothing modified -> save() not called


def test_non_saml_connection_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """An LDAP connection is never touched even if it carries the key."""
    conn: dict[str, object] = {"type": "ldap", "id": "ldap_corp", "owned_by_site": "central"}
    saved = _run(monkeypatch, [conn])

    assert saved is None  # ldap is skipped, so no modification
