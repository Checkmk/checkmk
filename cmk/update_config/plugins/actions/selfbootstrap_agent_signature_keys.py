#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Rewrite the agent signature keys file to self-bootstrap its variable

``cmk.gui.config.load_config()`` executes all files below ``multisite.d``.
The bakery's ``multisite.d/wato/agent_signature_keys.mk`` was written in bare
``agent_signature_keys.update({...})`` style by earlier Checkmk versions,
which can only be executed if the variable was pre-seeded into the exec
namespace — a side effect of the full GUI plug-in registration (feature
config defaults). Processes that load the GUI config without that
registration (upcoming: the cmk-post-rename-site rename actions during
``omd restore`` / ``omd cp`` / ``omd mv``) fail on such files:

    NameError: name 'agent_signature_keys' is not defined

The ``KeypairStore`` now persists a self-bootstrapping file; re-save files
written by earlier versions through it.
"""

from logging import Logger
from typing import override

from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.registry import update_action_registry
from cmk.utils import paths
from cmk.utils.keypair_store import KeypairStore

_SELF_BOOTSTRAP_MARKER = "locals().setdefault"


class SelfbootstrapAgentSignatureKeys(UpdateAction):
    """Make the persisted signature keys loadable without pre-seeded defaults"""

    @override
    def __call__(self, logger: Logger) -> None:
        path = paths.default_config_dir / "multisite.d/wato/agent_signature_keys.mk"
        if not path.exists() or _SELF_BOOTSTRAP_MARKER in path.read_text():
            return

        keypair_store = KeypairStore(path, "agent_signature_keys")
        keypair_store.save(keypair_store.load())
        logger.info("Rewrote %(path)s to self-bootstrap its variable", {"path": path})


update_action_registry.register(
    SelfbootstrapAgentSignatureKeys(
        name="selfbootstrap_agent_signature_keys",
        title="Make the agent signature keys file self-bootstrap",
        sort_index=30,
        expiry_version=ExpiryVersion.CMK_310,
    )
)
