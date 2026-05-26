#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Strip the deprecated ``owned_by_site`` attribute from SAML connections.

``owned_by_site`` on ``SAMLUserConnectionConfig`` previously scoped SAML login
buttons to the connection's owning site. The new per-site
``authentication_connections`` field replaces that mechanism with an explicit
list, so ``owned_by_site`` is dead data. The field has been removed from the
TypedDict; this action strips it from existing on-disk records so the
configuration matches the new schema and pydantic validation does not flag the
extra key.
"""

from logging import Logger
from typing import cast, override

from cmk.gui.config import active_config
from cmk.gui.userdb import UserConnectionConfigFile
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.log import VERBOSE


class RemoveSAMLOwnedBySite(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        config_file = UserConnectionConfigFile()
        connections = config_file.load_for_modification()

        modified = False
        for connection in connections:
            if connection["type"] != "saml2":
                continue
            raw = cast(dict[str, object], connection)
            if "owned_by_site" not in raw:
                continue
            owner = raw.pop("owned_by_site")
            modified = True
            logger.log(
                VERBOSE,
                "Removed owned_by_site=%r from SAML connection %r",
                owner,
                connection.get("id"),
            )

        if modified:
            config_file.save(connections, pprint_value=active_config.wato_pprint_config)


update_action_registry.register(
    RemoveSAMLOwnedBySite(
        name="remove_saml_owned_by_site",
        title="Strip deprecated owned_by_site attribute from SAML connections",
        # Independent of the sites-config migrations; pick any sort_index after
        # the cluster of site-config actions so logs read sensibly.
        sort_index=40,
        expiry_version=ExpiryVersion.CMK_310,
    )
)
