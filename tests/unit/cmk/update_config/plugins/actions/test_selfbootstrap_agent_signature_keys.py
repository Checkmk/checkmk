#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import cmk.utils.paths
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.selfbootstrap_agent_signature_keys import (
    SelfbootstrapAgentSignatureKeys,
)
from cmk.utils.keypair_store import KeypairStore

_ACTION = SelfbootstrapAgentSignatureKeys(
    name="selfbootstrap_agent_signature_keys",
    title="Make the agent signature keys file self-bootstrap",
    sort_index=30,
    expiry_version=ExpiryVersion.CMK_310,
)

_RAW_KEY = {
    "certificate": "cert-pem",
    "private_key": "key-pem",
    "alias": "my key",
    "owner": "admin",
    "date": 1234567890.0,
    "not_downloaded": False,
}


def _exec_without_defaults(content: str) -> dict[str, object]:
    """Load a config file the way an unregistered process does"""
    namespace: dict[str, object] = {}
    exec(compile(content, "<config-file>", "exec"), {}, namespace)
    return namespace


def test_rewrites_bare_file() -> None:
    path = cmk.utils.paths.default_config_dir / "multisite.d/wato/agent_signature_keys.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(f"agent_signature_keys.update({ ({1: _RAW_KEY})!r})\n")
        keys_before = KeypairStore(path, "agent_signature_keys").load()

        _ACTION(logging.getLogger(__name__))

        namespace = _exec_without_defaults(path.read_text())
        assert KeypairStore.parse(namespace["agent_signature_keys"]) == keys_before  # type: ignore[arg-type]
    finally:
        path.unlink(missing_ok=True)


def test_keeps_self_bootstrapping_file() -> None:
    path = cmk.utils.paths.default_config_dir / "multisite.d/wato/agent_signature_keys.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        KeypairStore(path, "agent_signature_keys").save({})
        content = path.read_text()

        _ACTION(logging.getLogger(__name__))

        assert path.read_text() == content
    finally:
        path.unlink(missing_ok=True)


def test_missing_file_is_fine() -> None:
    _ACTION(logging.getLogger(__name__))
