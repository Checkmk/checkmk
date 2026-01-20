#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override

from cmk.ccc.site import omd_site, SiteId
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.certs import cert_dir, RelaysCA
from cmk.utils.log import VERBOSE
from cmk.utils.paths import omd_root


class CreateRelayCA(UpdateAction):
    """Initialize relay CA if it doesn't exist.

    The relay CA is used for signing certificates for relay connections.
    Sites upgraded from versions before relay CA introduction need this.
    """

    @override
    def __call__(
        self, logger: Logger, site_root: Path | None = None, site_id: SiteId | None = None
    ) -> None:
        if site_root is None:
            site_root = Path(omd_root)

        ca_path = cert_dir(site_root)
        ca_file = RelaysCA._ca_file(ca_path)

        if ca_file.exists():
            logger.log(VERBOSE, "Relay CA already exists, skipping.")
            return

        logger.log(VERBOSE, "Creating relay CA.")
        if site_id is None:
            site_id = SiteId(omd_site())
        RelaysCA.load_or_create(ca_path, site_id)


update_action_registry.register(
    CreateRelayCA(
        name="create-relay-ca",
        title="Create relay CA",
        sort_index=100,  # No ordering constraints
        expiry_version=ExpiryVersion.CMK_300,  # Expires at 2.6, for 2.5 only
        continue_on_failure=True,
    )
)
